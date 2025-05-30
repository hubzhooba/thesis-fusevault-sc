import { useState, useEffect } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Paper, 
  Grid, 
  TextField, 
  Button, 
  Divider, 
  Avatar, 
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Link,
  Chip,
  IconButton,
  InputAdornment,
  Tooltip
} from '@mui/material';
import { 
  Save, 
  AccountCircle, 
  LocationOn, 
  Work, 
  Business, 
  Twitter, 
  LinkedIn, 
  GitHub,
  Add,
  Image,
  Badge
} from '@mui/icons-material';
import { useUser } from '../hooks/useUser';
import { useAuth } from '../contexts/AuthContext';
import { useTransactions } from '../hooks/useTransactions';
import { useAssets } from '../hooks/useAssets';
import { formatWalletAddress, formatDate } from '../utils/formatters';

function ProfilePage() {
  const { user, isLoading, isError, update, isUpdating } = useUser();
  const { currentAccount, signOut } = useAuth();
  const { summary, isSummaryLoading, allTransactions, getAllTransactions } = useTransactions();
  const { assets } = useAssets();
  
  // Fetch all transactions when profile loads
  useEffect(() => {
    if (currentAccount) {
      getAllTransactions();
    }
  }, [currentAccount, getAllTransactions]);
  const [tabValue, setTabValue] = useState(0);
  
  // Initialize form data from user data
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    organization: '',
    job_title: '',
    bio: '',
    profile_image: '',
    location: '',
    twitter: '',
    linkedin: '',
    github: ''
  });

  // Update form data when user data changes
  useEffect(() => {
    if (user) {
      // Check if the user object actually has data
      console.log('User data received:', user);
      
      setFormData({
        email: user.email || '',
        name: user.name || '',
        organization: user.organization || '',
        job_title: user.job_title || '',
        bio: user.bio || '',
        profile_image: user.profile_image || '',
        location: user.location || '',
        twitter: user.twitter || '',
        linkedin: user.linkedin || '',
        github: user.github || ''
      });
    }
  }, [user]);

  // Handle form changes
  const handleChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value
    });
  };

  // Handle tab changes
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();
    
    // Remove empty fields to avoid overwriting with empty values
    const updateData = {};
    Object.entries(formData).forEach(([key, value]) => {
      if (value) updateData[key] = value;
    });
    
    update(updateData);
  };

  // Get avatar from profile image or initials
  const getAvatar = () => {
    if (formData.profile_image) {
      return (
        <Avatar 
          src={formData.profile_image} 
          alt={formData.name || 'User'} 
          sx={{ width: 100, height: 100, mb: 2 }}
        />
      );
    } else {
      const initials = formData.name 
        ? formData.name.split(' ').map(n => n[0]).join('').toUpperCase() 
        : 'EU';
      
      return (
        <Avatar sx={{ width: 100, height: 100, mb: 2, bgcolor: 'primary.main', fontSize: '2rem' }}>
          {initials}
        </Avatar>
      );
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Profile Settings
      </Typography>
      
      <Grid container spacing={4}>
        {/* Profile Information Section */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ mb: 4 }}>
            <Tabs 
              value={tabValue} 
              onChange={handleTabChange} 
              variant="fullWidth"
              indicatorColor="primary"
              textColor="primary"
            >
              <Tab label="Personal Info" />
              <Tab label="Professional" />
              <Tab label="Social Media" />
            </Tabs>
            
            <Divider />
            
            {isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : isError ? (
              <Box sx={{ p: 3 }}>
                <Alert severity="error" sx={{ mb: 3 }}>
                  Error loading profile data. Please try again later.
                </Alert>
              </Box>
            ) : (
              <form onSubmit={handleSubmit}>
                {/* Personal Info Tab */}
                {tabValue === 0 && (
                  <Box sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      Personal Information
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <TextField
                          label="Email Address"
                          type="email"
                          fullWidth
                          value={formData.email}
                          onChange={handleChange('email')}
                          margin="normal"
                          required
                        />
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <TextField
                          label="Full Name"
                          fullWidth
                          value={formData.name}
                          onChange={handleChange('name')}
                          margin="normal"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <Badge />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <TextField
                          label="Location"
                          fullWidth
                          value={formData.location}
                          onChange={handleChange('location')}
                          margin="normal"
                          placeholder="City, Country"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <LocationOn />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                      
                      <Grid item xs={12}>
                        <TextField
                          label="Profile Image URL"
                          fullWidth
                          value={formData.profile_image}
                          onChange={handleChange('profile_image')}
                          margin="normal"
                          placeholder="https://example.com/image.jpg"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <Image />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                      
                      <Grid item xs={12}>
                        <TextField
                          label="Bio"
                          multiline
                          rows={4}
                          fullWidth
                          value={formData.bio}
                          onChange={handleChange('bio')}
                          margin="normal"
                          placeholder="Tell us about yourself..."
                        />
                      </Grid>
                    </Grid>
                  </Box>
                )}
                
                {/* Professional Tab */}
                {tabValue === 1 && (
                  <Box sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      Professional Information
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          label="Organization"
                          fullWidth
                          value={formData.organization}
                          onChange={handleChange('organization')}
                          margin="normal"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <Business />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <TextField
                          label="Job Title"
                          fullWidth
                          value={formData.job_title}
                          onChange={handleChange('job_title')}
                          margin="normal"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <Work />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                    </Grid>
                  </Box>
                )}
                
                {/* Social Media Tab */}
                {tabValue === 2 && (
                  <Box sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      Social Media
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <TextField
                          label="Twitter/X Handle"
                          fullWidth
                          value={formData.twitter}
                          onChange={handleChange('twitter')}
                          margin="normal"
                          placeholder="@username"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <Twitter />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                      
                      <Grid item xs={12}>
                        <TextField
                          label="LinkedIn Profile"
                          fullWidth
                          value={formData.linkedin}
                          onChange={handleChange('linkedin')}
                          margin="normal"
                          placeholder="linkedin.com/in/username"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <LinkedIn />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                      
                      <Grid item xs={12}>
                        <TextField
                          label="GitHub Username"
                          fullWidth
                          value={formData.github}
                          onChange={handleChange('github')}
                          margin="normal"
                          InputProps={{
                            startAdornment: (
                              <InputAdornment position="start">
                                <GitHub />
                              </InputAdornment>
                            ),
                          }}
                        />
                      </Grid>
                    </Grid>
                  </Box>
                )}
                
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
                    disabled={isUpdating}
                    startIcon={isUpdating ? <CircularProgress size={24} /> : <Save />}
                  >
                    {isUpdating ? 'Saving...' : 'Save Changes'}
                  </Button>
                </Box>
              </form>
            )}
          </Paper>
        </Grid>
        
        {/* Wallet Information Sidebar */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 4 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
              {getAvatar()}
              
              <Typography variant="h6" align="center" gutterBottom>
                {user?.name || 'Ethereum User'}
              </Typography>
              
              <Typography variant="body2" align="center" color="text.secondary" gutterBottom>
                {currentAccount ? formatWalletAddress(currentAccount, 8, 8) : 'Not connected'}
              </Typography>
              
              {user?.job_title && (
                <Chip 
                  icon={<Work fontSize="small" />} 
                  label={user.job_title} 
                  size="small" 
                  sx={{ mb: 1 }} 
                />
              )}
              
              {user?.organization && (
                <Chip 
                  icon={<Business fontSize="small" />} 
                  label={user.organization} 
                  size="small" 
                  sx={{ mb: 1 }} 
                />
              )}
              
              {user?.location && (
                <Chip 
                  icon={<LocationOn fontSize="small" />} 
                  label={user.location} 
                  size="small" 
                  sx={{ mb: 1 }} 
                />
              )}
              
              <Box sx={{ mt: 2 }}>
                <Button 
                  variant="outlined" 
                  color="primary"
                  onClick={signOut}
                >
                  Disconnect Wallet
                </Button>
              </Box>
            </Box>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Account Summary
            </Typography>
            
            {isSummaryLoading ? (
              <CircularProgress size={24} />
            ) : (
              <Box>
                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Total Assets:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" fontWeight="bold">
                      {assets.length || summary.unique_assets || allTransactions?.filter(tx => tx.action?.includes('CREATE')).length || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Transactions:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" fontWeight="bold">
                      {allTransactions?.length || summary.total_transactions || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Creates:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {allTransactions?.filter(tx => tx.action?.includes('CREATE')).length || summary.actions?.CREATE || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Updates:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {allTransactions?.filter(tx => tx.action?.includes('UPDATE')).length || summary.actions?.UPDATE || 0}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Deletes:
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2">
                      {allTransactions?.filter(tx => tx.action?.includes('DELETE')).length || summary.actions?.DELETE || 0}
                    </Typography>
                  </Grid>
                  
                  {user?.created_at && (
                    <>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Member Since:
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          {formatDate(user.created_at)}
                        </Typography>
                      </Grid>
                    </>
                  )}
                  
                  {user?.last_login && (
                    <>
                      <Grid item xs={6}>
                        <Typography variant="body2" color="text.secondary">
                          Last Login:
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="body2">
                          {formatDate(user.last_login)}
                        </Typography>
                      </Grid>
                    </>
                  )}
                </Grid>
              </Box>
            )}
            
            {/* Social Media Links */}
            {(user?.twitter || user?.linkedin || user?.github) && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Connect
                </Typography>
                
                <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                  {user?.twitter && (
                    <Tooltip title={`Twitter: ${user.twitter}`}>
                      <IconButton 
                        color="primary" 
                        component="a" 
                        href={`https://twitter.com/${user.twitter.replace('@', '')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Twitter />
                      </IconButton>
                    </Tooltip>
                  )}
                  
                  {user?.linkedin && (
                    <Tooltip title="LinkedIn Profile">
                      <IconButton 
                        color="primary" 
                        component="a" 
                        href={user.linkedin.startsWith('http') ? user.linkedin : `https://linkedin.com/in/${user.linkedin}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <LinkedIn />
                      </IconButton>
                    </Tooltip>
                  )}
                  
                  {user?.github && (
                    <Tooltip title={`GitHub: ${user.github}`}>
                      <IconButton 
                        color="primary" 
                        component="a" 
                        href={`https://github.com/${user.github}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <GitHub />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default ProfilePage;