import axios from "axios";

const createAnalyticAPI = () => {
  const token = localStorage.getItem("token");

  const api = axios.create({
    baseURL: `https://rau-place.ru/api/`,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? "Token " + token : undefined
    }
  });

  api.interceptors.request.use(
    config => {
      const updatedToken = localStorage.getItem("token");
      if (updatedToken) {
        config.headers['Authorization'] = `Token ${updatedToken}`;
      }
      return config;
    },
    error => {
      return Promise.reject(error);
    }
  );

  return api;
};

export const analyticAPI = createAnalyticAPI();
