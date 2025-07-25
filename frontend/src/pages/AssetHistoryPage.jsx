import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Container,
    Typography,
    Box,
    Paper,
    Button,
    CircularProgress,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    Alert,
    Card,
    CardContent,
    Grid,
    Divider,
    IconButton,
    Tooltip,
    TextField,
    InputAdornment,
    MenuItem,
    FormControl,
    InputLabel,
    Select,
    Pagination,
    Stack
} from '@mui/material';
import {
    ArrowBack,
    History,
    Refresh,
    Download,
    Search,
    FilterList,
    Visibility,
    Edit,
    VerifiedUser,
    Warning
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { transactionService } from '../services/transactionService';
import { assetService } from '../services/assetService';
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

function AssetHistoryPage() {
    const { assetId } = useParams();
    const navigate = useNavigate();

    // State management
    const [history, setHistory] = useState([]);
    const [asset, setAsset] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [actionFilter, setActionFilter] = useState('all');
    const [page, setPage] = useState(1);
    const [rowsPerPage, setRowsPerPage] = useState(25);

    // Fetch asset details and history
    useEffect(() => {
        const fetchData = async () => {
            if (!assetId) return;

            setLoading(true);
            try {
                // Fetch asset details and history in parallel
                const [assetData, historyData] = await Promise.all([
                    assetService.retrieveMetadata(assetId).catch(() => null), // Don't fail if asset fetch fails
                    transactionService.getAssetHistory(assetId)
                ]);

                setAsset(assetData);
                setHistory(historyData.transactions || []);
                setError(null);
            } catch (err) {
                console.error('Error fetching asset history:', err);
                setError('Failed to load asset history. Please try again later.');
                toast.error('Error loading asset history');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [assetId]);

    // Refresh history
    const handleRefresh = async () => {
        setRefreshing(true);
        try {
            const historyData = await transactionService.getAssetHistory(assetId);
            setHistory(historyData.transactions || []);
            toast.success('History refreshed');
        } catch (err) {
            console.error('Error refreshing history:', err);
            toast.error('Failed to refresh history');
        } finally {
            setRefreshing(false);
        }
    };

    // Filter transactions based on search and action filter
    const filteredHistory = history.filter(transaction => {
        // Action filter
        if (actionFilter !== 'all' && transaction.action !== actionFilter) {
            return false;
        }

        // Search filter
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            return (
                transaction.action?.toLowerCase().includes(searchLower) ||
                transaction.walletAddress?.toLowerCase().includes(searchLower) ||
                transaction.metadata?.smartContractTxId?.toLowerCase().includes(searchLower) ||
                transaction.metadata?.reason?.toLowerCase().includes(searchLower)
            );
        }

        return true;
    });

    // Get unique actions for filter dropdown
    const availableActions = [...new Set(history.map(tx => tx.action).filter(Boolean))].sort();

    // Get action color for chips
    const getActionColor = (action) => {
        switch (action) {
            case 'CREATE': return 'success';
            case 'VERSION_CREATE': return 'info';
            case 'UPDATE': return 'info';
            case 'DELETE': return 'error';
            case 'RECREATE_DELETED': return 'success';
            case 'INTEGRITY_RECOVERY': return 'warning';
            case 'TRANSFER_INITIATED': return 'secondary';
            case 'TRANSFER_COMPLETED': return 'success';
            case 'TRANSFER_CANCELLED': return 'error';
            case 'DELETION_STATUS_RESTORED': return 'warning';
            default: return 'default';
        }
    };

    // Handle export to CSV
    const handleExport = () => {
        try {
            // Create CSV headers
            const headers = [
                'Date & Time',
                'Action',
                'Version',
                'Owner',
                'Initiator',
                'Transaction Hash',
                'Details'
            ];

            // Convert transactions to CSV rows
            const csvData = filteredHistory.map(tx => [
                formatDate(tx.timestamp),
                tx.action || '',
                tx.version || tx.metadata?.versionNumber || tx.metadata?.new_version || 
                    (tx.action === 'CREATE' || tx.action === 'RECREATE_DELETED' ? '1' : 'N/A'),
                tx.walletAddress || '',
                tx.performedBy || tx.walletAddress || '',
                tx.metadata?.smartContractTxId || 
                    (['UPDATE', 'INTEGRITY_RECOVERY', 'DELETION_STATUS_RESTORED'].includes(tx.action) ? 'N/A' : 'Pending'),
                tx.metadata?.reason || tx.metadata?.description || 'No additional details'
            ]);

            // Combine headers and data
            const allRows = [headers, ...csvData];
            
            // Convert to CSV string
            const csvContent = allRows
                .map(row => row.map(field => `"${field}"`).join(','))
                .join('\n');

            // Create and download file
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `asset-history-${assetId}-${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            toast.success(`Exported ${filteredHistory.length} transactions to CSV`);
        } catch (error) {
            console.error('Export error:', error);
            toast.error('Failed to export asset history');
        }
    };

    // Handle pagination
    const handlePageChange = (event, newPage) => {
        setPage(newPage);
    };

    const handleRowsPerPageChange = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(1); // Reset to first page when changing rows per page
    };

    // Calculate pagination
    const totalPages = Math.ceil(filteredHistory.length / rowsPerPage);
    const startIndex = (page - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    const paginatedHistory = filteredHistory
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(startIndex, endIndex);

    // Loading state
    if (loading) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
                    <Box sx={{ textAlign: 'center' }}>
                        <CircularProgress size={60} />
                        <Typography variant="h6" sx={{ mt: 2 }}>
                            Loading asset history...
                        </Typography>
                    </Box>
                </Box>
            </Container>
        );
    }

    // Error state
    if (error) {
        return (
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                        variant="outlined"
                        startIcon={<ArrowBack />}
                        onClick={() => navigate('/dashboard')}
                    >
                        Back to Dashboard
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={<Refresh />}
                        onClick={() => window.location.reload()}
                    >
                        Try Again
                    </Button>
                </Box>
            </Container>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Button
                    variant="outlined"
                    startIcon={<ArrowBack />}
                    onClick={() => navigate('/dashboard')}
                    sx={{ mr: 2 }}
                >
                    Back
                </Button>
                <History sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="h4" sx={{ flexGrow: 1 }}>
                    Asset History
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Refresh History">
                        <IconButton
                            onClick={handleRefresh}
                            disabled={refreshing}
                            color="primary"
                        >
                            <Refresh />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Export History">
                        <IconButton
                            onClick={handleExport}
                            color="primary"
                        >
                            <Download />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {/* Asset Info Card */}
            {asset && (
                <Card sx={{ mb: 3 }}>
                    <CardContent>
                        <Grid container spacing={2} alignItems="center">
                            <Grid item xs={12} md={8}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    <Typography variant="h6">
                                        {asset.criticalMetadata?.name || 'Untitled Asset'}
                                    </Typography>
                                    {asset.verification?.verified && !asset.verification?.recoveryNeeded && (
                                        <Tooltip title="Asset critical metadata authenticity verified. No integrity issues detected.">
                                            <Chip
                                                icon={<VerifiedUser />}
                                                label="Verified"
                                                color="success"
                                                size="small"
                                                variant="outlined"
                                            />
                                        </Tooltip>
                                    )}
                                    {asset.verification?.recoveryNeeded && asset.verification?.recoverySuccessful && (
                                        <Tooltip title="Asset metadata was automatically restored from blockchain due to potential tampering. View recovery details in transaction history below.">
                                            <Chip
                                                icon={<Warning />}
                                                label="Metadata Restored"
                                                color="warning"
                                                size="small"
                                                variant="outlined"
                                            />
                                        </Tooltip>
                                    )}
                                    {asset.verification?.recoveryNeeded && !asset.verification?.recoverySuccessful && (
                                        <Tooltip title="Asset integrity could not be verified and recovery failed. Contact support for assistance. View recovery details in transaction history below.">
                                            <Chip
                                                icon={<Warning />}
                                                label="Integrity Compromised"
                                                color="error"
                                                size="small"
                                                variant="outlined"
                                            />
                                        </Tooltip>
                                    )}
                                </Box>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    Asset ID: {assetId}
                                </Typography>
                                {asset.criticalMetadata?.description && (
                                    <Typography variant="body2" color="text.secondary">
                                        {asset.criticalMetadata.description}
                                    </Typography>
                                )}
                            </Grid>
                            <Grid item xs={12} md={4}>
                                <Box sx={{ display: 'flex', gap: 1, justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        startIcon={<Visibility />}
                                        onClick={() => navigate(`/assets/${assetId}`)}
                                    >
                                        View Asset
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        size="small"
                                        startIcon={<Edit />}
                                        onClick={() => navigate(`/assets/${assetId}?edit=true`)}
                                    >
                                        Edit Asset
                                    </Button>
                                </Box>
                            </Grid>
                        </Grid>
                    </CardContent>
                </Card>
            )}

            {/* Summary Stats */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="primary">
                                {history.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Total Transactions
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="secondary">
                                {availableActions.length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Different Actions
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card>
                        <CardContent sx={{ textAlign: 'center' }}>
                            <Typography variant="h4" color="warning.main">
                                {history.filter(tx => tx.action === 'INTEGRITY_RECOVERY').length}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Integrity Recoveries
                            </Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Filters */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={6} md={4}>
                        <TextField
                            fullWidth
                            placeholder="Search transactions..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            InputProps={{
                                startAdornment: (
                                    <InputAdornment position="start">
                                        <Search />
                                    </InputAdornment>
                                ),
                            }}
                            size="small"
                        />
                    </Grid>
                    <Grid item xs={12} sm={6} md={4}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Filter by Action</InputLabel>
                            <Select
                                value={actionFilter}
                                label="Filter by Action"
                                onChange={(e) => setActionFilter(e.target.value)}
                                startAdornment={
                                    <InputAdornment position="start">
                                        <FilterList />
                                    </InputAdornment>
                                }
                            >
                                <MenuItem value="all">All Actions</MenuItem>
                                {availableActions.map(action => (
                                    <MenuItem key={action} value={action}>
                                        {action}
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Per Page</InputLabel>
                            <Select
                                value={rowsPerPage}
                                label="Per Page"
                                onChange={handleRowsPerPageChange}
                            >
                                <MenuItem value={10}>10</MenuItem>
                                <MenuItem value={25}>25</MenuItem>
                                <MenuItem value={50}>50</MenuItem>
                                <MenuItem value={100}>100</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} md={2}>
                        <Typography variant="body2" color="text.secondary">
                            Showing {startIndex + 1}-{Math.min(endIndex, filteredHistory.length)} of {filteredHistory.length} transactions
                        </Typography>
                    </Grid>
                </Grid>
            </Paper>

            {/* History Table */}
            <Paper>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Date & Time</TableCell>
                                <TableCell>Action</TableCell>
                                <TableCell>Version</TableCell>
                                <TableCell>Owner</TableCell>
                                <TableCell>Initiator</TableCell>
                                <TableCell>Transaction Hash</TableCell>
                                <TableCell>Details</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {paginatedHistory.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                                        <Typography variant="body2" color="text.secondary">
                                            {filteredHistory.length === 0
                                                ? (history.length === 0 ? 'No transaction history found for this asset.' : 'No transactions match your current filters.')
                                                : 'No transactions on this page.'
                                            }
                                        </Typography>
                                        {history.length > 0 && filteredHistory.length === 0 && (
                                            <Button
                                                variant="text"
                                                onClick={() => {
                                                    setSearchTerm('');
                                                    setActionFilter('all');
                                                }}
                                                sx={{ mt: 1 }}
                                            >
                                                Clear Filters
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ) : (
                                paginatedHistory.map((transaction, index) => (
                                        <TableRow
                                            key={transaction.id || transaction._id || index}
                                            hover
                                            sx={{ '&:nth-of-type(odd)': { bgcolor: 'action.hover' } }}
                                        >
                                            <TableCell>
                                                <Typography variant="body2">
                                                    {formatDate(transaction.timestamp)}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={transaction.action}
                                                    color={getActionColor(transaction.action)}
                                                    size="small"
                                                    variant="outlined"
                                                    icon={transaction.action === 'INTEGRITY_RECOVERY' ? 
                                                        (transaction.metadata?.error_message || transaction.metadata?.reason?.includes('failed') ? <Warning /> : <VerifiedUser />) 
                                                        : undefined}
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" fontFamily="monospace">
                                                    {transaction.version || 
                                                     transaction.metadata?.versionNumber || 
                                                     transaction.metadata?.new_version ||
                                                     (transaction.action === 'CREATE' || transaction.action === 'RECREATE_DELETED' ? '1' : 'N/A')}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Tooltip title={transaction.walletAddress}>
                                                    <Typography variant="body2" fontFamily="monospace">
                                                        {formatWalletAddress(transaction.walletAddress)}
                                                    </Typography>
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell>
                                                <Tooltip title={transaction.performedBy || transaction.walletAddress}>
                                                    <Typography variant="body2" fontFamily="monospace">
                                                        {transaction.performedBy ? 
                                                            formatWalletAddress(transaction.performedBy) : 
                                                            formatWalletAddress(transaction.walletAddress)}
                                                    </Typography>
                                                </Tooltip>
                                            </TableCell>
                                            <TableCell>
                                                {transaction.metadata?.smartContractTxId ? (
                                                    <Tooltip title={transaction.metadata.smartContractTxId}>
                                                        <Typography variant="body2" fontFamily="monospace" color="primary.main">
                                                            {formatTransactionHash(transaction.metadata.smartContractTxId)}
                                                        </Typography>
                                                    </Tooltip>
                                                ) : (
                                                    // Actions that don't involve blockchain writes should show N/A
                                                    ['UPDATE', 'INTEGRITY_RECOVERY', 'DELETION_STATUS_RESTORED'].includes(transaction.action) ? (
                                                        <Typography variant="body2" color="text.secondary">
                                                            N/A
                                                        </Typography>
                                                    ) : (
                                                        <Chip label="Pending" size="small" color="warning" variant="outlined" />
                                                    )
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {transaction.action === 'INTEGRITY_RECOVERY' && transaction.metadata ? (
                                                    <Box>
                                                        {!(transaction.metadata?.error_message || transaction.metadata?.reason?.includes('failed')) && transaction.metadata.blockchain_cid && transaction.metadata.computed_cid && (
                                                            <Typography variant="caption" display="block">
                                                                Restored critical metadata from IPFS
                                                            </Typography>
                                                        )}
                                                        {!(transaction.metadata?.error_message || transaction.metadata?.reason?.includes('failed')) && transaction.metadata.tx_hash_corrected && (
                                                            <Typography variant="caption" display="block">
                                                                Original TX ID restored from blockchain
                                                            </Typography>
                                                        )}
                                                        {transaction.metadata?.error_message || transaction.metadata?.reason?.includes('failed') ? (
                                                            <Box>
                                                                {transaction.metadata?.reason?.includes('transaction and event methods failed') && (
                                                                    <Typography variant="caption" display="block">
                                                                        Unable to retrieve original TX ID
                                                                    </Typography>
                                                                )}
                                                                {transaction.metadata?.reason?.includes('retrieved metadata from IPFS is invalid') && (
                                                                    <Typography variant="caption" display="block">
                                                                        Unable to restore critical metadata from IPFS
                                                                    </Typography>
                                                                )}
                                                                <Typography variant="caption" display="block">
                                                                    Status: Recovery failed
                                                                </Typography>
                                                            </Box>
                                                        ) : (
                                                            <Typography variant="caption" display="block">
                                                                Status: Successfully recovered
                                                            </Typography>
                                                        )}
                                                    </Box>
                                                ) : (
                                                    <Typography variant="body2">
                                                        {transaction.metadata?.reason ||
                                                            transaction.metadata?.description ||
                                                            'No additional details'}
                                                    </Typography>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                {/* Pagination Controls */}
                {filteredHistory.length > 0 && (
                    <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
                        <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                            <Typography variant="caption" color="text.secondary">
                                Last updated: {new Date().toLocaleString()}
                                {refreshing && ' • Refreshing...'}
                            </Typography>
                            {totalPages > 1 && (
                                <Pagination
                                    count={totalPages}
                                    page={page}
                                    onChange={handlePageChange}
                                    color="primary"
                                    size="small"
                                    showFirstButton
                                    showLastButton
                                />
                            )}
                        </Stack>
                    </Box>
                )}
            </Paper>

            {/* Action Buttons */}
            <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'center' }}>
                <Button
                    variant="outlined"
                    onClick={() => navigate('/dashboard')}
                >
                    Back to Dashboard
                </Button>
                {asset && (
                    <>
                        <Button
                            variant="outlined"
                            startIcon={<Visibility />}
                            onClick={() => navigate(`/assets/${assetId}`)}
                        >
                            View Asset Details
                        </Button>
                        <Button
                            variant="contained"
                            startIcon={<Edit />}
                            onClick={() => navigate(`/assets/${assetId}?edit=true`)}
                        >
                            Edit Asset
                        </Button>
                    </>
                )}
            </Box>
        </Container>
    );
}

export default AssetHistoryPage;