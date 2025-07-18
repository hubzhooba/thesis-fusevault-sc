import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  TextField,
  MenuItem,
  InputAdornment,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Divider,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  Button,
  Pagination,
  Stack
} from '@mui/material';
import {
  Search,
  FilterList,
  History,
  Refresh,
  Download
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { transactionService } from '../services/transactionService';
import { useAuth } from '../contexts/AuthContext';
import { useTransactions } from '../hooks/useTransactions';
import { formatDate, formatWalletAddress, formatTransactionHash } from '../utils/formatters';

function HistoryPage() {
  const { currentAccount, isAuthenticated } = useAuth();
  const { summary, isSummaryLoading } = useTransactions();
  
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Fetch transaction data
  useEffect(() => {
    const fetchTransactions = async () => {
      if (!currentAccount || !isAuthenticated) return;
      
      setLoading(true);
      try {
        // Get all transactions for the user
        const response = await transactionService.getAllTransactions(currentAccount);
        setTransactions(response.transactions || []);
        setError(null);
      } catch (err) {
        console.error('Error fetching transactions:', err);
        setError('Failed to load transaction history. Please try again later.');
        toast.error('Error loading transaction history');
      } finally {
        setLoading(false);
      }
    };

    fetchTransactions();
  }, [currentAccount, isAuthenticated]);

  // Refresh transactions
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const response = await transactionService.getAllTransactions(currentAccount);
      setTransactions(response.transactions || []);
      setError(null);
      toast.success('Transaction history refreshed');
    } catch (err) {
      console.error('Error refreshing transactions:', err);
      toast.error('Failed to refresh transaction history');
    } finally {
      setRefreshing(false);
    }
  };

  // Filter transactions based on action type and search term
  const filteredTransactions = transactions.filter(tx => {
    // Filter by action type
    if (filter !== 'all' && tx.action !== filter) {
      return false;
    }
    
    // Filter by search term (asset ID, wallet address, or transaction hash)
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      return (
        tx.assetId?.toLowerCase().includes(searchLower) ||
        tx.walletAddress?.toLowerCase().includes(searchLower) ||
        tx.performedBy?.toLowerCase().includes(searchLower) ||
        tx.metadata?.smartContractTxId?.toLowerCase().includes(searchLower)
      );
    }
    
    return true;
  });

  // Get unique actions for filter dropdown
  const availableActions = [...new Set(transactions.map(tx => tx.action).filter(Boolean))].sort();

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
        'Asset ID', 
        'Action',
        'Owner',
        'Initiator',
        'Transaction Hash'
      ];

      // Convert transactions to CSV rows
      const csvData = filteredTransactions.map(tx => [
        formatDate(tx.timestamp),
        tx.assetId || '',
        tx.action || '',
        tx.walletAddress || '',
        tx.performedBy || tx.walletAddress || '',
        tx.metadata?.smartContractTxId || 'N/A'
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
      link.setAttribute('download', `transaction-history-${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast.success(`Exported ${filteredTransactions.length} transactions to CSV`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Failed to export transactions');
    }
  };

  // Handle filter change
  const handleFilterChange = (event) => {
    setFilter(event.target.value);
    setPage(1); // Reset to first page when filter changes
  };

  // Handle search term change
  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
    setPage(1); // Reset to first page when search changes
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
  const totalPages = Math.ceil(filteredTransactions.length / rowsPerPage);
  const startIndex = (page - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const paginatedTransactions = filteredTransactions
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
              Loading transaction history...
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
            variant="contained"
            startIcon={<Refresh />}
            onClick={handleRefresh}
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
        <History sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h4" sx={{ flexGrow: 1 }}>
          Transaction History
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

      {/* Summary Stats */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {transactions.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Transactions
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {transactions.filter(tx => ['CREATE', 'RECREATE_DELETED'].includes(tx.action)).length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Asset Creations
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="info.main">
                {transactions.filter(tx => ['UPDATE', 'VERSION_CREATE'].includes(tx.action)).length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Asset Modifications
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="error.main">
                {transactions.filter(tx => tx.action === 'DELETE').length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Asset Deletions
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
              onChange={handleSearchChange}
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
                value={filter}
                label="Filter by Action"
                onChange={handleFilterChange}
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
              Showing {startIndex + 1}-{Math.min(endIndex, filteredTransactions.length)} of {filteredTransactions.length} transactions
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
                <TableCell>Asset ID</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Owner</TableCell>
                <TableCell>Initiator</TableCell>
                <TableCell>Transaction Hash</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedTransactions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body2" color="text.secondary">
                      {filteredTransactions.length === 0 
                        ? (transactions.length === 0 ? 'No transaction history found.' : 'No transactions match your current filters.')
                        : 'No transactions on this page.'}
                    </Typography>
                    {transactions.length > 0 && filteredTransactions.length === 0 && (
                      <Button
                        variant="text"
                        onClick={() => {
                          setSearchTerm('');
                          setFilter('all');
                        }}
                        sx={{ mt: 1 }}
                      >
                        Clear Filters
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ) : (
                paginatedTransactions.map((transaction, index) => (
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
                        <Tooltip title={`View ${transaction.assetId} details`}>
                          <Button
                            variant="text"
                            size="small"
                            onClick={() => window.open(`/assets/${transaction.assetId}`, '_blank')}
                            sx={{ 
                              textTransform: 'none',
                              fontFamily: 'monospace',
                              maxWidth: 120,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis'
                            }}
                          >
                            {transaction.assetId}
                          </Button>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={transaction.action}
                          color={getActionColor(transaction.action)}
                          size="small"
                          variant="outlined"
                        />
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
                    </TableRow>
                  ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Pagination Controls */}
        {filteredTransactions.length > 0 && (
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
    </Container>
  );
}

export default HistoryPage;