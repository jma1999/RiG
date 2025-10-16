// Determine API base URL based on environment
const getApiBase = () => {
  // If VITE_API_URL is explicitly set, use it
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/?$/, "");
  }
  
  // In production (Vercel), try to use the deployed API URL
  if (import.meta.env.PROD) {
    // You can set this to your actual deployed API URL
    return "https://your-api-domain.com"; // Replace with your actual API URL
  }
  
  // In development, use localhost
  return "http://127.0.0.1:8000";
};

export const API_BASE = getApiBase();
