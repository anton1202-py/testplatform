import React from "react";
import "../../styles/connections.css"
import {OrdersCartTab} from "./OrdersCartTab";
import {OrdersAccountsTab} from "./OrdersAccountsTab";

export const OrdersTabs = ({sortBy, setLoading, platformsToFilter, setPlatformsToFilter, accountsToFilter,setAccountsToFilter, showCartTab, showAccountsTab, setOrdersItems, setShowCartTab, setShowAccountsTab, ordersType}) => {
  return (
    <div className="control-tabs">
      {showCartTab ? <OrdersCartTab sortBy={sortBy} setLoading={setLoading} platforms={platformsToFilter} setPlatformsToFilter={setPlatformsToFilter} accountsToFilter={accountsToFilter} setShowCartTab={setShowCartTab} showCartTab={showCartTab} setOrdersItems={setOrdersItems} ordersType={ordersType}/> : <></>}
      {showAccountsTab ? <OrdersAccountsTab sortBy={sortBy} setLoading={setLoading} platformsToFilter={platformsToFilter} accountsToFilter={accountsToFilter} setAccountsToFilter={setAccountsToFilter} setOrdersItems={setOrdersItems} showAccountsTab={showAccountsTab} setShowAccountsTab={setShowAccountsTab} ordersType={ordersType}/> : <></>}
    </div>
  )
}
