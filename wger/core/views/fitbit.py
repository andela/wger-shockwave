import os, base64, requests, urllib
from django.conf import settings

class Fitbit():
    '''
    Integration of fitbit data
    '''
    CLIENT_ID     = os.getenv('FITAPP_CONSUMER_KEY')
    CLIENT_SECRET = os.getenv('FITAPP_CONSUMER_SECRET')
    REDIRECT_URI  = os.getenv('REDIRECT_URI','http://localhost:8000/en/fitbit/complete/') 

    # Decide which information the fitbit.py should have access to.
    # Options: 'activity', 'heartrate', 'location', 'nutrition',
    #          'profile', 'settings', 'sleep', 'social', 'weight'
    API_SCOPES    = ('activity', 'heartrate', 'location', 'nutrition', 'profile', 'settings', 'sleep', 'social', 'weight')

    API_SERVER    = 'api.fitbit.com'
    WWW_SERVER    = 'www.fitbit.com'
    AUTHORIZATION_URL = 'https://%s/oauth2/authorize' % WWW_SERVER
    ACCESS_TOKEN_URL     = 'https://%s/oauth2/token' % API_SERVER

    def GetAuthorizationUri(self):

        # Parameters for authorization, make sure to select 
        params = {
            'client_id': self.CLIENT_ID,
            'response_type':  'code',
            'scope': ' '.join(self.API_SCOPES),
            'redirect_uri': self.REDIRECT_URI
        }

        # Encode parameters and construct authorization url to be returned to user.
        urlparams = urllib.parse.urlencode(params)
        return "%s?%s" % (self.AUTHORIZATION_URL, urlparams)


    # Tokens are requested based on access code. Access code must be fresh (10 minutes)
    def GetAccessToken(self, access_code):

        # Construct the auth header
        client_id = self.CLIENT_ID.encode('utf-8')
        secret = self.CLIENT_SECRET.encode('utf-8')
        # auth_header = base64.b64encode(client_id + b':' + secret)
        headers = {
            'Authorization': 'Basic %s' % os.getenv('AUTH'),
            'Content-Type' : 'application/x-www-form-urlencoded'
        }

        params = {
            'code': access_code,
            'grant_type': 'authorization_code',
            'client_id': self.CLIENT_ID,
            'redirect_uri': self.REDIRECT_URI
        }
        
        resp = requests.post(self.ACCESS_TOKEN_URL, data=params, headers=headers)
        status_code = resp.status_code
        resp = resp.json()

        if status_code != 200:
            raise Exception("Something went wrong exchanging code for token (%s): %s" % (resp['errors'][0]['errorType'], resp['errors'][0]['message']))

        token = dict()
        token['access_token']  = resp['access_token']
        token['refresh_token'] = resp['refresh_token']

        return token

    # Get new tokens if auth token expires
    def RefreshAccessToken(self, token):

        # Construct the authentication header
        client_id = self.CLIENT_ID.encode('utf-8')
        secret = self.CLIENT_SECRET.encode('utf-8')
        auth_header = base64.b64encode(client_id + b':' + secret)
        headers = {
            'Authorization': 'Basic %s' % auth_header,
            'Content-Type' : 'application/x-www-form-urlencoded'
        }

        # Set up parameters for refresh request
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token']
        }

        resp = requests.post(self.ACCESS_TOKEN_URL, data=params, headers=headers)

        status_code = resp.status_code
        resp = resp.json()

        if status_code != 200:
            raise Exception("Something went wrong refreshing (%s): %s" % (resp['errors'][0]['errorType'], resp['errors'][0]['message']))

        token['access_token']  = resp['access_token']
        token['refresh_token'] = resp['refresh_token']

        return token

    # Place api call to retrieve data
    def ApiCall(self, token, apiCall='/1/user/-/activities/log/steps/date/today/1d.json'):
        # Other API Calls possible, or read the FitBit documentation for the full list
        # (https://dev.fitbit.com/docs/), e.g.:
        # apiCall = '/1/user/-/devices.json'
        # apiCall = '/1/user/-/profile.json'
        # apiCall = '/1/user/-/activities/date/2015-10-22.json'

        headers = {
            'Authorization': 'Bearer %s' % token['access_token']
        }

        final_url = 'https://' + self.API_SERVER + apiCall

        resp = requests.get(final_url, headers=headers)

        status_code = resp.status_code

        resp = resp.json()
        resp['token'] = token

        if status_code == 200:
            return resp
        elif status_code == 401:
            # Refresh the access token with the refresh token if expired. Access tokens should be good for 1 hour.
            token = self.RefreshAccessToken(token)
            self.ApiCall(token, apiCall)
        else:
            raise Exception("Something went wrong requesting (%s): %s" % (resp['errors'][0]['errorType'], resp['errors'][0]['message']))