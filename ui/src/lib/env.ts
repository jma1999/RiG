const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE.replace(/\/?$/, "");
  }
  return "http://127.0.0.1:8000";
};

export const API_BASE = getApiBase();
