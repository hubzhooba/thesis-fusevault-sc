import httpx
import logging
import os
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv
from app.utilities.format import format_json, get_ipfs_metadata

logger = logging.getLogger(__name__)

class IPFSService:
    def __init__(self):
        load_dotenv()
        self.storage_service_url = os.getenv("WEB3_STORAGE_SERVICE_URL")
        if not self.storage_service_url:
            self.storage_service_url = "http://localhost:8080"  # Default fallback
            logger.warning("WEB3_STORAGE_SERVICE_URL not set, using default: http://localhost:8080")

    async def store_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Store metadata on IPFS.
        
        Args:
            metadata: Metadata to store on IPFS
            
        Returns:
            String CID of the stored metadata
        """
        try:
            formatted_metadata = format_json(get_ipfs_metadata(metadata))

            files = {"files": ("metadata.json", formatted_metadata, "application/json")}

            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(f"{self.storage_service_url}/upload", files=files)
                response.raise_for_status()

            # Get the response JSON and log it for debugging
            response_json = response.json()
            logger.debug(f"IPFS service response: {response_json}")

            # Extract CID from the response
            if "cids" in response_json and len(response_json["cids"]) > 0 and "cid" in response_json["cids"][0]:
                cid_dict = response_json["cids"][0]["cid"]
                if isinstance(cid_dict, dict) and "/" in cid_dict:
                    cid = cid_dict["/"]
                else:
                    cid = str(cid_dict)
            else:
                raise ValueError(f"Unable to extract CID from response: {response_json}")
            
            if not cid:
                raise ValueError(f"Unable to extract CID from response: {response_json}")

            logger.info(f"Successfully stored metadata on IPFS. CID: {cid}")
            return cid

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error uploading to IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error uploading metadata to IPFS: {str(e)}")
            raise

    async def retrieve_metadata(self, cid: str) -> Dict[str, Any]:
        """
        Retrieve metadata from IPFS by CID.
        
        Args:
            cid: Content identifier to retrieve
            
        Returns:
            Dict containing the metadata
        """
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.get(f"{self.storage_service_url}/file/{cid}/contents")
                response.raise_for_status()

            metadata = response.json()
            logger.info(f"Successfully retrieved metadata from IPFS with CID: {cid}")
            return metadata

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error retrieving from IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error retrieving metadata from IPFS: {str(e)}")
            raise
            
    async def upload_files(self, files: List[UploadFile]) -> Dict[str, Any]:
        """
        Upload multiple files to IPFS.
        
        Args:
            files: List of files to upload
            
        Returns:
            Dict containing result information including CIDs
        """
        try:
            # Prepare multipart form data for multiple files
            multipart_data = []
            for file in files:
                file_content = await file.read()
                multipart_data.append(
                    ("files", (file.filename, file_content, file.content_type))
                )
            
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.storage_service_url}/upload",
                    files=multipart_data
                )
                response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully uploaded {len(files)} files to IPFS")
            return result
            
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error uploading files to IPFS: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error uploading files to IPFS: {str(e)}")
            raise
            
    async def get_file_url(self, cid: str) -> Dict[str, Any]:
        """
        Get the URL for a file stored on IPFS.
        
        Args:
            cid: Content identifier of the file
            
        Returns:
            Dict containing the URL information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.storage_service_url}/file/{cid}")
                response.raise_for_status()
                
            result = response.json()
            return result
            
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error getting file URL: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error getting file URL: {str(e)}")
            raise
            
    async def get_file_contents(self, cid: str, response_type: str = "text") -> Any:
        """
        Get the contents of a file stored on IPFS.
        
        Args:
            cid: Content identifier of the file
            response_type: Type of response to return ('text', 'json', or 'bytes')
            
        Returns:
            The file contents in the specified format
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.storage_service_url}/file/{cid}/contents")
                response.raise_for_status()
                
            if response_type == "json":
                return response.json()
            elif response_type == "bytes":
                return response.content
            else:
                return response.text
                
        except httpx.HTTPError as exc:
            logger.error(f"HTTP error getting file contents: {str(exc)}")
            raise
        except Exception as e:
            logger.error(f"General error getting file contents: {str(e)}")
            raise
    
    async def compute_cid(self, metadata: Dict[str, Any]) -> str:
        """
        Compute CID from given metadata by interacting with IPFS Node service.
        
        Args:
            metadata: Metadata to compute CID for
            
        Returns:
            Computed CID string
        
        Raises:
            HTTPException: If there's an error computing the CID
        """
        try:
            # Format the metadata using the consistent format_json utility
            formatted_metadata = format_json(metadata)
            
            # Create a file content for direct multipart upload
            files = {
                "file": ("metadata.json", formatted_metadata, "application/json")
            }

            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.storage_service_url}/calculate-cid",
                    files=files
                )
                response.raise_for_status()

            result = response.json()
            computed_cid = result.get("computed_cid")
            
            if not computed_cid:
                raise ValueError("No CID returned from IPFS service")
                
            return computed_cid

        except Exception as e:
            logger.error(f"Error computing CID: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def verify_cid(self, metadata: Dict[str, Any], provided_cid: str) -> bool:
        """
        Compares provided CID against computed CID from metadata.
        
        Args:
            metadata: Metadata to verify
            provided_cid: CID to compare against
            
        Returns:
            Boolean indicating whether CIDs match
            
        Raises:
            HTTPException: If there's an error verifying the CID
        """
        try:
            # Extract only the IPFS-relevant fields from the metadata if needed
            ipfs_metadata = get_ipfs_metadata(metadata)
            
            # Calculate the CID based on the filtered metadata
            computed_cid = await self.compute_cid(ipfs_metadata)
            
            # Compare the CIDs
            return computed_cid == provided_cid
            
        except Exception as e:
            logger.error(f"Error verifying CID: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
