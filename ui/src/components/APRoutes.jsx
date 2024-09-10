import {LoginPage} from "../pages/LoginPage";
import {BrowserRouter as Router, Redirect, Route, Switch} from 'react-router-dom';
import {ConnectionsPage} from "../pages/ConnectionsPage";
import {NavigationPanel} from "./NavigationPanel";
import {useAuth} from "./AuthProvider";
import {OrdersPage} from "../pages/OrdersPage";

export const APRoutes = () => {
  const {token} = useAuth()
  return (
    <Router>
      <Switch>
        {
          !token ? (
            <Route path="*">
              <Redirect to="/login"/>
              <Route exact path="/login" component={LoginPage} />
            </Route>
          ) : (
            <>
              <NavigationPanel />
              <Route exact path="/login" component={LoginPage} />
              <Route exact path="/" component={ConnectionsPage}></Route>
              <Route exact path="/orders" component={OrdersPage}></Route>
            </>
          )
        }

      </Switch>
    </Router>

  )
}
