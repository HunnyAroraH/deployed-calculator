import os
import logging
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load environment variables (for local development and deployment)
load_dotenv()

# Scopes for Google Drive and Docs APIs
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Authenticate and return credentials
def get_creds():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Use environment variables for OAuth credentials
            creds = InstalledAppFlow.from_client_config({
                "installed": {
                    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                    "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                    "auth_uri": os.getenv('GOOGLE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
                    "token_uri": os.getenv('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
                    "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
                    "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                    "redirect_uris": os.getenv('GOOGLE_REDIRECT_URIS', 'http://localhost:5000/').split(',')
                }
            }, SCOPES).run_local_server(port=0)

        # Save the credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

# Upload the `.docx` file and convert it to Google Docs format
def upload_and_convert_to_gdoc(service, template_file):
    logging.info(f"Uploading and converting {template_file} to Google Docs format.")
    file_metadata = {
        'name': 'Converted Google Doc', 
        'mimeType': 'application/vnd.google-apps.document'  # Specify conversion to Google Docs format
    }
    media = MediaFileUpload(template_file, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    document_id = uploaded_file.get('id')
    logging.info(f"Uploaded and converted .docx file. Document ID: {document_id}")
    return document_id

# Replace placeholders with "Click here"
def replace_with_click_here(docs_service, document_id, tag_to_link):
    requests = []
    for tag, link in tag_to_link.items():
        logging.debug(f"Replacing tag {tag} with 'Click here'.")
        requests.append({
            'replaceAllText': {
                'containsText': {
                    'text': tag,
                    'matchCase': True,
                },
                'replaceText': "Click here"
            }
        })
    try:
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
        logging.info(f"Replaced tags with 'Click here' in document ID: {document_id}")
    except Exception as e:
        logging.error(f"Error replacing text in document: {e}")

# Apply hyperlinks and bold styling to "Click here" text
def apply_hyperlinks(docs_service, document_id, tag_to_link):
    document = docs_service.documents().get(documentId=document_id).execute()
    content = document.get('body').get('content', [])
    requests = []
    applied_links = {}
    for element in content:
        if 'paragraph' in element:
            for run in element.get('paragraph').get('elements', []):
                text_run = run.get('textRun')
                if text_run and 'Click here' in text_run.get('content', ''):
                    start_index = run.get('startIndex')
                    end_index = run.get('endIndex')
                    for tag, link in tag_to_link.items():
                        if tag not in applied_links:
                            logging.debug(f"Applying link: {link} to 'Click here'.")
                            applied_links[tag] = True
                            requests.append({
                                'updateTextStyle': {
                                    'range': {
                                        'startIndex': start_index,
                                        'endIndex': end_index
                                    },
                                    'textStyle': {
                                        'bold': True,
                                        'link': {
                                            'url': link
                                        }
                                    },
                                    'fields': 'bold,link'
                                }
                            })
                            break
    try:
        for i in range(0, len(requests), 50):
            chunk = requests[i:i + 50]
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': chunk}).execute()
        logging.info(f"Applied hyperlinks and bold styling in document ID: {document_id}")
    except Exception as e:
        logging.error(f"Error applying hyperlinks and styling in document: {e}")

# Replace IBO name and ID placeholders
def replace_ibo_details(docs_service, document_id, ibo_name, ibo_id):
    requests = [
        {
            'replaceAllText': {
                'containsText': {
                    'text': '{ibo_name}',
                    'matchCase': True
                },
                'replaceText': ibo_name
            }
        },
        {
            'replaceAllText': {
                'containsText': {
                    'text': '{ibo_id}',
                    'matchCase': True
                },
                'replaceText': ibo_id
            }
        }
    ]
    try:
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
        logging.info(f"Replaced IBO details in document ID: {document_id}")
    except Exception as e:
        logging.error(f"Error replacing IBO details in document: {e}")

# Share the document by making it public
def share_google_doc(drive_service, document_id):
    logging.info(f"Sharing Google Doc {document_id} publicly.")
    drive_service.permissions().create(
        fileId=document_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    logging.info(f"Document shared: https://docs.google.com/document/d/{document_id}/edit")

# Main function to generate the Google Doc
def generate_google_doc(basic_data_filename):
    creds = get_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # Step 2: Load the IBO-specific JSON file with links and details
    with open(basic_data_filename, 'r') as json_file:
        links_data = json.load(json_file)

    tag_to_link = {
        '{xoom_residential}': links_data['shop_links'][2],
        '{id_seal}': links_data['shop_links'][3],
        '{impact_residential}': links_data['shop_links'][4],
        '{truvvi_lifestyle}': links_data['shop_links'][1],
        '{directv_residential}': links_data['shop_links'][6],
        # Add remaining tags here...
    }

    # IBO details from the basic data JSON file
    ibo_name = links_data['ibo_name']
    ibo_id = links_data['ibo_id']

    # Step 3: Upload and convert the template to Google Docs format
    template_file = 'ServiceLinkTemplate.docx'
    document_id = upload_and_convert_to_gdoc(drive_service, template_file)

    # Step 4: Replace placeholders with "Click here" text
    replace_with_click_here(docs_service, document_id, tag_to_link)

    # Step 5: Apply hyperlinks and bold styling to "Click here" text
    apply_hyperlinks(docs_service, document_id, tag_to_link)

    # Step 6: Replace IBO details
    replace_ibo_details(docs_service, document_id, ibo_name, ibo_id)

    # Step 7: Share the Google Doc publicly
    share_google_doc(drive_service, document_id)

    # Return the Google Doc URL
    return f"https://docs.google.com/document/d/{document_id}/edit"
