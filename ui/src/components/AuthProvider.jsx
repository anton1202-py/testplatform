import React, {
  createContext,
  useContext, useEffect,
  useMemo,
  useState,
} from "react";

const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [token, setToken_] = useState(localStorage.getItem("token"));
  const [login, setLogin] = useState(localStorage.getItem("username"))

  const setToken = (newToken) => {
    localStorage.setItem("token", newToken);
    setToken_(newToken);
  };

  useEffect(()=>{
    localStorage.setItem("username", login)
  }, [login])

  const contextValue = useMemo(() => ({ token, setToken, setLogin, login}), [token, login]);

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};

export default AuthProvider;
