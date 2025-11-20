import React, { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  FileUp,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { API_BASE } from '@/lib/env';

const UploadStatus = {
  IDLE: 'idle',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

const DirectUploadComponent = ({ onUploadComplete, onUploadError }) => {
  const [uploadStatus, setUploadStatus] = useState(UploadStatus.IDLE);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [error, setError] = useState(null);
  const [uploadSession, setUploadSession] = useState(null);
  const [uploadedParts, setUploadedParts] = useState([]);
  
  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);
  const statusPollingRef = useRef(null);

  const startStatusPolling = useCallback((jobId) => {
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current);
    }
    
    statusPollingRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/jobs/${jobId}`);
        if (response.ok) {
          const status = await response.json();
          setJobStatus(status);
          
          if (status.status === 'completed') {
            setUploadStatus(UploadStatus.COMPLETED);
            setUploadProgress(100);
            clearInterval(statusPollingRef.current);
            if (onUploadComplete) {
              onUploadComplete(status);
            }
          } else if (status.status === 'failed') {
            setUploadStatus(UploadStatus.FAILED);
            setError(status.message);
            clearInterval(statusPollingRef.current);
            if (onUploadError) {
              onUploadError(status.message);
            }
          } else {
            setUploadProgress(status.progress || 0);
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 2000); // Poll every 2 seconds
  }, [onUploadComplete, onUploadError]);

  const uploadFilePart = async (file, partNumber, presignedUrl) => {
    const start = (partNumber - 1) * uploadSession.min_part_size;
    const end = Math.min(start + uploadSession.min_part_size, file.size);
    const chunk = file.slice(start, end);
    
    const response = await fetch(presignedUrl, {
      method: 'PUT',
      body: chunk,
      headers: {
        'Content-Type': 'application/octet-stream'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to upload part ${partNumber}: ${response.statusText}`);
    }
    
    const etag = response.headers.get('ETag');
    return { PartNumber: partNumber, ETag: etag };
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.ifc')) {
      setError('Please select an IFC file');
      return;
    }
    
    // Validate file size (1GB limit)
    const maxSize = 1024 * 1024 * 1024; // 1GB
    if (file.size > maxSize) {
      setError('File size exceeds 1GB limit');
      return;
    }
    
    setError(null);
    setUploadStatus(UploadStatus.UPLOADING);
    setUploadProgress(0);
    
    try {
      // Step 1: Create upload session
      const sessionResponse = await fetch(`${API_BASE}/upload/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: file.name,
          file_size: file.size,
          content_type: file.type || 'application/octet-stream',
          tenant_id: 'default'
        })
      });
      
      if (!sessionResponse.ok) {
        throw new Error(`Failed to create upload session: ${sessionResponse.statusText}`);
      }
      
      const session = await sessionResponse.json();
      setUploadSession(session);
      
      // Step 2: Upload file parts
      const totalParts = Math.ceil(file.size / session.min_part_size);
      const parts = [];
      
      abortControllerRef.current = new AbortController();
      
      for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
        if (abortControllerRef.current?.signal.aborted) {
          throw new Error('Upload cancelled');
        }
        
        // Get presigned URL for this part
        const partUrlResponse = await fetch(
          `${API_BASE}/upload/part/${session.upload_id}/${partNumber}?file_key=${encodeURIComponent(session.file_key)}`
        );
        
        if (!partUrlResponse.ok) {
          throw new Error(`Failed to get upload URL for part ${partNumber}`);
        }
        
        const partData = await partUrlResponse.json();
        
        // Upload the part
        const partResult = await uploadFilePart(file, partNumber, partData.presigned_url);
        parts.push(partResult);
        
        // Update progress
        const progress = Math.round((partNumber / totalParts) * 50); // 50% for upload
        setUploadProgress(progress);
      }
      
      // Step 3: Complete upload and start processing
      const completeResponse = await fetch(
        `${API_BASE}/upload/complete/${session.upload_id}?file_key=${encodeURIComponent(session.file_key)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parts)
        }
      );
      
      if (!completeResponse.ok) {
        throw new Error(`Failed to complete upload: ${completeResponse.statusText}`);
      }
      
      const completeData = await completeResponse.json();
      setJobId(completeData.job_id);
      setUploadStatus(UploadStatus.PROCESSING);
      setUploadProgress(50); // Start processing at 50%
      
      // Start polling for job status
      startStatusPolling(completeData.job_id);
      
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message);
      setUploadStatus(UploadStatus.FAILED);
      
      // Abort upload session if it exists
      if (uploadSession) {
        try {
          await fetch(
            `${API_BASE}/upload/abort/${uploadSession.upload_id}?file_key=${encodeURIComponent(uploadSession.file_key)}`,
            { method: 'DELETE' }
          );
        } catch (abortErr) {
          console.error('Failed to abort upload:', abortErr);
        }
      }
      
      if (onUploadError) {
        onUploadError(err.message);
      }
    }
  };

  const cancelUpload = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current);
    }
    
    if (uploadSession) {
      try {
        await fetch(
          `${API_BASE}/upload/abort/${uploadSession.upload_id}?file_key=${encodeURIComponent(uploadSession.file_key)}`,
          { method: 'DELETE' }
        );
      } catch (err) {
        console.error('Failed to abort upload:', err);
      }
    }
    
    if (jobId) {
      try {
        await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
      } catch (err) {
        console.error('Failed to cancel job:', err);
      }
    }
    
    setUploadStatus(UploadStatus.CANCELLED);
    setUploadProgress(0);
  };

  const resetUpload = () => {
    setUploadStatus(UploadStatus.IDLE);
    setUploadProgress(0);
    setJobId(null);
    setJobStatus(null);
    setError(null);
    setUploadSession(null);
    setUploadedParts([]);
    
    if (statusPollingRef.current) {
      clearInterval(statusPollingRef.current);
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getStatusIcon = () => {
    switch (uploadStatus) {
      case UploadStatus.UPLOADING:
      case UploadStatus.PROCESSING:
        return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
      case UploadStatus.COMPLETED:
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case UploadStatus.FAILED:
        return <XCircle className="h-5 w-5 text-red-600" />;
      case UploadStatus.CANCELLED:
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return <Upload className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusText = () => {
    switch (uploadStatus) {
      case UploadStatus.UPLOADING:
        return 'Uploading file...';
      case UploadStatus.PROCESSING:
        return jobStatus?.message || 'Processing IFC file...';
      case UploadStatus.COMPLETED:
        return 'Upload and processing completed!';
      case UploadStatus.FAILED:
        return 'Upload failed';
      case UploadStatus.CANCELLED:
        return 'Upload cancelled';
      default:
        return 'Ready to upload';
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getStatusIcon()}
          IFC File Upload
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {uploadStatus === UploadStatus.IDLE && (
          <div className="text-center space-y-4">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8">
              <FileUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Upload IFC File
              </h3>
              <p className="text-gray-600 mb-4">
                Select an IFC file to upload and process. Maximum file size: 1GB
              </p>
              <Button
                onClick={() => fileInputRef.current?.click()}
                className="bg-gradient-to-r from-[var(--palantir-text-accent)] to-[#2563eb] hover:from-[#2563eb] hover:to-[#1d4ed8] text-white font-medium shadow-sm hover:shadow-md transition-all duration-200"
              >
                <Upload className="h-4 w-4 mr-2" />
                Choose File
              </Button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".ifc"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>
        )}

        {(uploadStatus === UploadStatus.UPLOADING || uploadStatus === UploadStatus.PROCESSING) && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{getStatusText()}</span>
              <Badge variant="outline">{uploadProgress}%</Badge>
            </div>
            <Progress value={uploadProgress} className="w-full" />
            <Button
              onClick={cancelUpload}
              variant="outline"
              size="sm"
              className="w-full"
            >
              Cancel Upload
            </Button>
          </div>
        )}

        {(uploadStatus === UploadStatus.COMPLETED || uploadStatus === UploadStatus.FAILED || uploadStatus === UploadStatus.CANCELLED) && (
          <div className="space-y-4">
            <div className="text-center">
              {getStatusIcon()}
              <p className="mt-2 text-sm font-medium">{getStatusText()}</p>
              {error && (
                <p className="mt-2 text-sm text-red-600">{error}</p>
              )}
              {jobStatus && (
                <div className="mt-4 text-xs text-gray-500">
                  <p>Job ID: {jobId}</p>
                  <p>Status: {jobStatus.status}</p>
                  {jobStatus.metadata && Object.keys(jobStatus.metadata).length > 0 && (
                    <p>Metadata: {JSON.stringify(jobStatus.metadata)}</p>
                  )}
                </div>
              )}
            </div>
            <Button
              onClick={resetUpload}
              variant="outline"
              className="w-full"
            >
              Upload Another File
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DirectUploadComponent;
