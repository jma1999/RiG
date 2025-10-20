"""
Cloud storage service for handling direct uploads to R2/S3.
"""
import os
import uuid
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Cloud storage configuration
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "rig-ifc-files")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "https://your-account-id.r2.cloudflarestorage.com")
R2_REGION = os.getenv("R2_REGION", "auto")

# File size limits
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "1073741824"))  # 1GB default
MIN_PART_SIZE = int(os.getenv("MIN_PART_SIZE", "5242880"))  # 5MB minimum part size


class CloudStorageService:
    """Service for managing cloud storage operations."""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name=R2_REGION
        )
        self.bucket_name = R2_BUCKET_NAME
    
    def create_multipart_upload_session(self, file_name: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        Create a multipart upload session for large file uploads.
        
        Args:
            file_name: Name of the file to upload
            content_type: MIME type of the file
            
        Returns:
            Dict containing upload session details
        """
        try:
            # Generate unique key for the file
            file_key = f"uploads/{uuid.uuid4()}/{file_name}"
            
            # Create multipart upload
            response = self.s3_client.create_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_key,
                ContentType=content_type,
                Metadata={
                    'original-filename': file_name,
                    'upload-timestamp': str(uuid.uuid4())
                }
            )
            
            upload_id = response['UploadId']
            
            return {
                "upload_id": upload_id,
                "file_key": file_key,
                "bucket": self.bucket_name,
                "endpoint_url": R2_ENDPOINT_URL,
                "region": R2_REGION,
                "max_file_size": MAX_FILE_SIZE,
                "min_part_size": MIN_PART_SIZE
            }
            
        except ClientError as e:
            raise Exception(f"Failed to create multipart upload: {str(e)}")
    
    def generate_presigned_url_for_part(self, file_key: str, upload_id: str, part_number: int) -> str:
        """
        Generate a presigned URL for uploading a specific part.
        
        Args:
            file_key: S3 key for the file
            upload_id: Multipart upload ID
            part_number: Part number (1-based)
            
        Returns:
            Presigned URL for the part upload
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'UploadId': upload_id,
                    'PartNumber': part_number
                },
                ExpiresIn=3600  # 1 hour
            )
            return url
            
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
    def complete_multipart_upload(self, file_key: str, upload_id: str, parts: list) -> Dict[str, Any]:
        """
        Complete a multipart upload.
        
        Args:
            file_key: S3 key for the file
            upload_id: Multipart upload ID
            parts: List of parts with ETags
            
        Returns:
            Dict containing completion results
        """
        try:
            response = self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
            return {
                "success": True,
                "file_url": response['Location'],
                "etag": response['ETag'],
                "bucket": self.bucket_name,
                "key": file_key
            }
            
        except ClientError as e:
            raise Exception(f"Failed to complete multipart upload: {str(e)}")
    
    def abort_multipart_upload(self, file_key: str, upload_id: str) -> bool:
        """
        Abort a multipart upload.
        
        Args:
            file_key: S3 key for the file
            upload_id: Multipart upload ID
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=self.bucket_name,
                Key=file_key,
                UploadId=upload_id
            )
            return True
            
        except ClientError as e:
            print(f"Failed to abort multipart upload: {str(e)}")
            return False
    
    def generate_download_url(self, file_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for downloading a file.
        
        Args:
            file_key: S3 key for the file
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned download URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expires_in
            )
            return url
            
        except ClientError as e:
            raise Exception(f"Failed to generate download URL: {str(e)}")
    
    def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_key: S3 key for the file
            
        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
            
        except ClientError as e:
            print(f"Failed to delete file: {str(e)}")
            return False
    
    def get_file_metadata(self, file_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file.
        
        Args:
            file_key: S3 key for the file
            
        Returns:
            Dict containing file metadata or None if not found
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return {
                "size": response['ContentLength'],
                "content_type": response['ContentType'],
                "last_modified": response['LastModified'],
                "etag": response['ETag'],
                "metadata": response.get('Metadata', {})
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise Exception(f"Failed to get file metadata: {str(e)}")
    
    def validate_file_type(self, file_name: str, content_type: str) -> bool:
        """
        Validate that the file is an IFC file.
        
        Args:
            file_name: Name of the file
            content_type: MIME type
            
        Returns:
            True if valid IFC file
        """
        # Check file extension
        if not file_name.lower().endswith('.ifc'):
            return False
        
        # Check MIME type (some browsers may not set this correctly)
        valid_types = [
            'application/octet-stream',
            'application/ifc',
            'text/plain',  # Some IFC files are served as text
            'model/ifc'
        ]
        
        return content_type.lower() in valid_types


# Global instance
cloud_storage = CloudStorageService()
