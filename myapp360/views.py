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


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("azure.identity").setLevel(logging.DEBUG)

@csrf_exempt
def list_files(request):
    # Log the Azure AD credentials being used
    print('TENANT_ID:', os.getenv('AZURE_TENANT_ID') or os.getenv('TENANT_ID'))
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


@csrf_exempt
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


# Create your views here.
def index(request):
    print('Request for index page received')
    return render(request, 'frontend/index.html')

@csrf_exempt
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
    
@csrf_exempt
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





@csrf_exempt
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
@csrf_exempt
def list_db_data(request):
    items = StudentDetails.objects.all()
    print(items)
    return render(request, 'frontend/list_db_data.html', {'items': items})


@csrf_exempt
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

@csrf_exempt
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

@csrf_exempt
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

