import boto3
import os
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()


class AWSService:
    def __init__(self, bucket_name=None):
        """
        Initialize AWS S3 client with credentials from environment variables
        
        Args:
            bucket_name: Optional bucket name to override the default from environment variables
        """
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION")
        self.bucket_name = bucket_name or os.getenv("AWS_S3_BUCKET")
        self.s3_client = None
        
        # Check if credentials are available but don't raise exception here
        # This allows the service to be instantiated and checked later
        if all([self.access_key, self.secret_key, self.bucket_name]):
            # Initialize S3 client
            self.config = Config(
                region_name=self.region,
                signature_version='s3v4',
                s3={
                    'addressing_style': 'virtual'  # Use virtual-hosted-style URLs
                }
            )
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=self.config
            )
    
    def check_credentials(self):
        """Check if AWS credentials are available and valid"""
        if not all([self.access_key, self.secret_key, self.bucket_name]):
            return {
                "success": False,
                "error": "Missing AWS credentials",
                "message": "Missing required AWS credentials or bucket name in environment variables"
            }
        
        if not self.s3_client:
            return {
                "success": False,
                "error": "S3 client not initialized",
                "message": "AWS S3 client could not be initialized. Check your credentials."
            }
        
        try:
            # Try a simple operation to verify credentials
            self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1
            )
            return {
                "success": True,
                "message": "AWS credentials are valid"
            }
        except NoCredentialsError:
            return {
                "success": False,
                "error": "Invalid AWS credentials",
                "message": "AWS credentials are invalid or insufficient permissions"
            }
        except ClientError as e:
            return {
                "success": False,
                "error": f"AWS S3 Error: {e.response['Error']['Code']}",
                "message": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "AWS credentials check failed",
                "message": str(e)
            }
        
    def upload_file(
        self, 
        file, 
        folder: str,
        content_type: str = None,
        file_name: str = None
    ) -> Dict[str, Any]:
        """
        Upload a file to S3 bucket
        
        Args:
            file: ServiceReportFiles-like object or path to a file
            folder: Folder path in S3 where the file will be uploaded
            content_type: Optional MIME type of the file
            file_name: Optional custom name for the file
            
        Returns:
            Dictionary containing upload results with file_key for database storage
        """
        # Check if credentials are valid
        cred_check = self.check_credentials()
        if not cred_check["success"]:
            return cred_check
            
        try:
            # Generate a unique file key based on service report ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of a UUID
            
            # Use provided filename or generate one
            if not file_name:
                file_name = f"file-{unique_id}"
                
            # Create S3 path: service_reports/[report_id]/[timestamp]_[filename]
            file_key = f"{folder}/{timestamp}_{file_name}"
            
            # If file is a path string, open and upload
            if isinstance(file, str):
                with open(file, 'rb') as f:
                    self.s3_client.upload_fileobj(
                        f, 
                        self.bucket_name, 
                        file_key,
                        ExtraArgs={
                            'ContentType': content_type
                        } if content_type else {}
                    )
            else:
                # Assume file is a file-like object
                self.s3_client.upload_fileobj(
                    file, 
                    self.bucket_name, 
                    file_key,
                    ExtraArgs={
                        'ContentType': content_type
                    } if content_type else {}
                )
                
            # Generate public URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
            
            return {
                "success": True,
                "file_key": file_key,
                "url": url,
                "folder": folder
            }
            
        except ClientError as e:
            return {
                "success": False,
                "error": f"AWS S3 Error: {e.response['Error']['Code']}",
                "message": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "ServiceReportFiles upload failed",
                "message": str(e)
            }
            
    def get_presigned_url(self, file_key: str, expires_in: int = 3600) -> Dict[str, Any]:
        """
        Generate a presigned URL for accessing a file
        
        Args:
            file_key: The key of the file in S3
            expires_in: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Dictionary with the presigned URL
        """
        # Check if credentials are valid
        cred_check = self.check_credentials()
        if not cred_check["success"]:
            return cred_check
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key
                },
                ExpiresIn=expires_in
            )
            
            return {
                "success": True,
                "url": url,
                "expires_in": expires_in
            }
            
        except ClientError as e:
            return {
                "success": False,
                "error": f"AWS S3 Error: {e.response['Error']['Code']}",
                "message": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Failed to generate presigned URL",
                "message": str(e)
            }
            
    def delete_file(self, file_key: str) -> Dict[str, Any]:
        """
        Delete a file from S3 bucket
        
        Args:
            file_key: The key of the file to delete
            
        Returns:
            Dictionary with delete operation result
        """
        # Check if credentials are valid
        cred_check = self.check_credentials()
        if not cred_check["success"]:
            return cred_check
            
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            return {
                "success": True,
                "message": f"ServiceReportFiles {file_key} deleted successfully"
            }
            
        except ClientError as e:
            return {
                "success": False,
                "error": f"AWS S3 Error: {e.response['Error']['Code']}",
                "message": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Failed to delete file",
                "message": str(e)
            }