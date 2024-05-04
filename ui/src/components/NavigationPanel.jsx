import {Link} from "react-router-dom";
import { useLocation } from 'react-router-dom'
import "../styles/connections.css"

export const NavigationPanel = () => {
  let pathName = useLocation().pathname
  return (
    <div className="nav">
      <div className="frame-wrapper">
        <img alt="" className="image-74" src="/images/nav_logo.svg"/>
        <Link to="/">
          <img alt="" className="container" src={pathName === "/" ? "/images/connections_active.svg": "/images/connections.svg"}/>
        </Link>
        <Link to="/orders">
          <img alt="" className="container" src={pathName === "/orders" ? "/images/stock_active.svg": "/images/stock.svg"}/>
        </Link>
      </div>
      <div className="frame-wrapper">
        <div className="frame-34298">
          <div className="frame-5746">
            <img alt="" className="navigation" src="/images/settings.svg"/>
            <img alt="" className="navigation" src="/images/navigation.svg"/>
            <img alt="" className="component-36" src="/images/profile.svg"/>
          </div>
        </div>
      </div>
    </div>
  )
}
