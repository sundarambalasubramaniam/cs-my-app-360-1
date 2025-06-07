from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
try:
    from azure.storage.blob import BlobServiceClient
except ImportError:
    BlobServiceClient = None
    print("Azure SDK is not installed. BlobServiceClient will not be available.")
import os
from .models import StudentDetails  
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
import os

from dotenv import load_dotenv
import logging

from azure.identity import get_bearer_token_provider
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import msal
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
import requests

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("azure.identity").setLevel(logging.DEBUG)



# Create your views here.


def login_page(request):
    """
    Renders the login page with a button to sign in with Microsoft Entra ID.
    """
    return render(request, 'frontend/login_page.html')

def azure_login(request):
    """
    Initiates the Azure AD login flow using MSAL.
    """
    authority = settings.AZURE_AD_AUTHORITY
    client_id = settings.AZURE_AD_CLIENT_ID
    redirect_uri = settings.AZURE_AD_REDIRECT_URI
    scope = settings.AZURE_AD_SCOPE
    msal_app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=settings.AZURE_AD_CLIENT_SECRET
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=scope,
        redirect_uri=redirect_uri
    )
    return redirect(auth_url)

def is_user_in_group(id_token_claims, required_group_id, access_token=None):
    """
    Checks if the user is a member of the required Entra group by group object ID.
    Always checks Graph API if not found in token claims.
    """
    print(f"DEBUG: Checking for required_group_id: {required_group_id}")
    groups = id_token_claims.get('groups', [])
    print(f"DEBUG: groups in id_token_claims: {groups}")
    if required_group_id in groups:
        print("DEBUG: User is in group via id_token_claims.")
        return True
    # Always check Graph API if not found in token
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://graph.microsoft.com/v1.0/me/memberOf?$select=id"
        response = requests.get(url, headers=headers)
        print(f"DEBUG: Graph API status: {response.status_code}")
        print(f"DEBUG: Full Graph API response: {response.text}")
        if response.status_code == 200:
            data = response.json()
            group_ids = [g['id'] for g in data.get('value', [])]
            print(f"DEBUG: group_ids from Graph API: {group_ids}")
            if required_group_id in group_ids:
                print("DEBUG: User is in group via Graph API.")
                return True
            else:
                print("DEBUG: User is NOT in group via Graph API.")
                return False
        else:
            print(f"Graph API error: {response.status_code} {response.text}")
            return False
    print("DEBUG: User is NOT in group (no group claim and no access token for Graph API).")
    return False

# Read group ID from environment variable
ENTRA_REQUIRED_GROUP_ID = os.getenv('ENTRA_USER_GROUP_ID')
print(f"DEBUG: ENTRA_REQUIRED_GROUP_ID at startup: {ENTRA_REQUIRED_GROUP_ID}")

@csrf_exempt
def azure_callback(request):
    """
    Handles the redirect from Azure AD and logs the user in if they are in the allowed group.
    """
    code = request.GET.get('code', None)
    if not code:
        return HttpResponse('No code returned from Azure AD.')
    authority = settings.AZURE_AD_AUTHORITY
    client_id = settings.AZURE_AD_CLIENT_ID
    redirect_uri = settings.AZURE_AD_REDIRECT_URI
    scope = settings.AZURE_AD_SCOPE
    msal_app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=settings.AZURE_AD_CLIENT_SECRET
    )
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=scope,
        redirect_uri=redirect_uri
    )
    if 'id_token_claims' in result:
        id_token_claims = result['id_token_claims']
        user_name = id_token_claims.get('name', 'User')
        user_email = id_token_claims.get('preferred_username', None)
        access_token = result.get('access_token')
        print("DEBUG: access_token in callback:", access_token)
        # Check group membership (handles overage with Graph API)
        if not is_user_in_group(id_token_claims, ENTRA_REQUIRED_GROUP_ID, access_token):
            return HttpResponseForbidden('Access denied: You are not a member of the required group.')
        # Create or get a Django user and log them in
        if user_email:
            user, created = User.objects.get_or_create(username=user_email, defaults={'first_name': user_name})
            auth_login(request, user)
        return render(request, 'frontend/login_success.html', {'name': user_name})
    else:
        return HttpResponse(f'Login failed: {result.get("error_description", "Unknown error")}', status=401)

@csrf_exempt
def login_success(request):
    """
    Renders the login success page after Azure AD authentication.
    """
    # You can retrieve user information from session or token here
    user_name = request.GET.get('name', 'User')
    return render(request, 'frontend/login_success.html', {'name': user_name})

@login_required(login_url='/')
def index(request):
    print('Request for index page received')
    return render(request, 'frontend/index.html')

@login_required(login_url='/')
def list_files(request):
    # Log the Azure AD credentials being used
    print('TENANT_ID:', os.getenv('AZURE_TENANT_ID') or os.getenv('AZURE_TENANT_ID'))
    print('CLIENT_ID:', os.getenv('AZURE_CLIENT_ID'))
    print('CLIENT_SECRET:', os.getenv('AZURE_CLIENT_SECRET'))
    print('SUBSCRIPTION_ID:', os.getenv('AZURE_SUBSCRIPTION_ID'))
    print('BLOB_CONTAINER_NAME:', os.getenv('AZURE_BLOB_CONTAINER_NAME'))
    print('STORAGE_ACCOUNT_URL:', os.getenv('AZURE_STORAGE_ACCOUNT_URL'))
    print('Using DefaultAzureCredential for authentication.')
    # Load environment variables from .env file
    load_dotenv()
    container_name = os.getenv('AZURE_BLOB_CONTAINER_NAME')
    if container_name is None:
        error_message = 'ERROR: BLOB_CONTAINER_NAME is not set. This is required for production environments.'
        logging.error(error_message)
        return HttpResponse(error_message)
    try:
        credential = DefaultAzureCredential()
        account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        if not account_url:
            print('ERROR: AZURE_STORAGE_ACCOUNT_URL is not set.')
            raise EnvironmentError("The Azure Storage account URL is not set in the environment variables.")
        print(f'Connecting to BlobServiceClient with account_url={account_url}')
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        container_client = blob_service_client.get_container_client(container_name)
        print(f'Attempting to list blobs in container: {container_name}')
        blobs = container_client.list_blobs()
        list_file_names = [blob.name for blob in blobs]
        print(f'Blobs found: {list_file_names}')
        return render(request, 'frontend/list_files.html', {'list_file_names': list_file_names})
    except Exception as e:
        import traceback
        print('Exception occurred while listing files:')
        traceback.print_exc()
        return HttpResponse(f"Error occurred: {e}")
#from dotenv import load_dotenv



@login_required(login_url='/')
def delete_file(request, file_name):
    """
    Deletes a file from the Azure Blob Storage container.
    """
    print(f"Request to delete file: {file_name}")
    container_name, account_url = load_azure_env_variables()
    if not account_url:
        return HttpResponse("The Azure Storage account URL is not set in the environment variables.")
    
    try:
        blob_client = get_blob_client(container_name, account_url, file_name)
        blob_client.delete_blob()
        print(f"File {file_name} deleted successfully.")
        return redirect('list_files')
    except Exception as e:
        print(f"Error occurred while deleting file {file_name}: {e}")
        return HttpResponse(f"Error occurred: {e}")




@login_required(login_url='/')
def hello(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name is None or name == '':
            print("Request for hello page received with no name or blank name -- redirecting")
            return redirect('index')
        else:
            print("Request for hello page received with name=%s" % name)
            context = {'name': name }
            return render(request, 'frontend/hello.html', context)
    else:
        return redirect('index')
    
@login_required(login_url='/')
def upload_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('myfile')
        if not uploaded_file:
            return handle_no_file_selected()
        return handle_file_upload(uploaded_file)
    else:
        return handle_no_file_selected()

def handle_no_file_selected():
    file_status_message = "File was NOT chosen...please select"
    print(file_status_message)
    return render(None, 'frontend/upload_file.html', {
        'file_status_message': file_status_message,
    })

def handle_file_upload(uploaded_file):
    print(f"Uploaded file: {uploaded_file.name}")
    container_name, account_url = load_azure_env_variables()
    if not account_url:
        return HttpResponse("The Azure Storage account URL is not set in the environment variables.")
    try:
        blob_client = get_blob_client(container_name, account_url, uploaded_file.name)
        blob_client.upload_blob(uploaded_file, overwrite=True)
        file_status_message = "File uploaded successfully."
        print(file_status_message)
        uploaded_file_url = blob_client.url
    except Exception as e:
        file_status_message = f"Error occurred during file upload: {e}"
        print(file_status_message)
        uploaded_file_url = None
    return render(None, 'frontend/upload_file.html', {
        'uploaded_file_url': uploaded_file_url,
        'file_status_message': file_status_message,
    })

def load_azure_env_variables():
    container_name = os.getenv('AZURE_BLOB_CONTAINER_NAME')
    account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
    return container_name, account_url

def get_blob_client(container_name, account_url, blob_name):
    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
    return blob_service_client.get_blob_client(container=container_name, blob=blob_name)





@login_required(login_url='/')
def list_files(request):
    # Log the Azure AD credentials being used
    print('TENANT_ID:', os.getenv('AZURE_TENANT_ID') or os.getenv('AZURE_TENANT_ID'))
    print('CLIENT_ID:', os.getenv('AZURE_CLIENT_ID'))
    print('CLIENT_SECRET:', os.getenv('AZURE_CLIENT_SECRET'))
    print('SUBSCRIPTION_ID:', os.getenv('AZURE_SUBSCRIPTION_ID'))
    print('BLOB_CONTAINER_NAME:', os.getenv('AZURE_BLOB_CONTAINER_NAME'))
    print('STORAGE_ACCOUNT_URL:', os.getenv('AZURE_STORAGE_ACCOUNT_URL'))
    print('Using DefaultAzureCredential for authentication.')

    container_name = os.getenv('AZURE_BLOB_CONTAINER_NAME')
    if container_name is None:
        logging.warning('ERROR: AZURE_BLOB_CONTAINER_NAME is not set.')
        return HttpResponse("The Azure Storage container name is not set in the environment variables.")

    try:
        credential = DefaultAzureCredential()
        account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        if not account_url:
            logging.error('ERROR: AZURE_STORAGE_ACCOUNT_URL is not set.')
            return HttpResponse("The Azure Storage account URL is not set in the environment variables.")
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        container_client = blob_service_client.get_container_client(container_name)
        print(f'Attempting to list blobs in container: {container_name}')
        blobs = container_client.list_blobs()
        list_file_names = [blob.name for blob in blobs]
        print(f'Blobs found: {list_file_names}')
        return render(request, 'frontend/list_files.html', {'list_file_names': list_file_names})
    except Exception as e:
        import traceback
        print('Exception occurred while listing files:')
        traceback.print_exc()
        return HttpResponse(f"Error occurred: {e}")

from django.core.paginator import Paginator


# This function retrieves all records from the StudentDetails model and renders them in the 'list_db_data.html' template.
@login_required(login_url='/')
def list_db_data(request):
    items = StudentDetails.objects.all()
    print(items)
    return render(request, 'frontend/list_db_data.html', {'items': items})

@login_required(login_url='/')
def upload_db_data(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        age = request.POST.get('age')
        if not name or not age:
            return HttpResponse("Name and age are required fields.")
        
        try:
            student = StudentDetails(name=name, age=age)
            student.save()
            return redirect('list_db_data')
        except Exception as e:
            return HttpResponse(f"Error saving data: {e}")
    else:
        return render(request, 'frontend/update_db_data.html')

@login_required(login_url='/')
def update_db_data(request):
    message = ""
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        if first_name and last_name and email:
            StudentDetails.objects.create(first_name=first_name, last_name=last_name, email=email)
            message = "User added successfully!"
        else:
            message = "All fields are required."
    return render(request, "frontend/update_db_data.html", {"message": message})

@login_required(login_url='/')
def delete_record(request, pk):
    if request.method == "POST":
        try:
            # The primary key in your model is user_id, not id
            item = StudentDetails.objects.get(user_id=pk)
            item.delete()
            return redirect('list_db_data')
        except StudentDetails.DoesNotExist:
            return HttpResponse("Item not found.")
    else:
        return HttpResponse("Item ID is required.")

