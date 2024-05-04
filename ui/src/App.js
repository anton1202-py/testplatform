import {APRoutes} from "./components/APRoutes";
import AuthProvider from "./components/AuthProvider";
import 'react-notifications/lib/notifications.css';
import { NotificationContainer } from 'react-notifications';


function App() {
  return (
    <AuthProvider>
      <APRoutes />
      <NotificationContainer />
    </AuthProvider>
  )
}

export default App;
