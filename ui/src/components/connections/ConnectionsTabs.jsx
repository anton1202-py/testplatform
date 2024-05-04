import {ConnectionsCartTab} from "./ConnectionsCartTab";
import {ConnectionsAccountsTab} from "./ConnectionsAccountsTab";
import React from "react";
import "../../styles/connections.css"

export const ConnectionsTabs = ({notLinkedSubtype, linkType, sortBy, setLoading, platformsToFilter, setPlatformsToFilter, accountsToFilter,setAccountsToFilter, showCartTab, showAccountsTab, setProducts, setShowCartTab, setShowAccountsTab}) => {
  return (
    <div className="control-tabs">
      {showCartTab ? <ConnectionsCartTab notLinkedSubtype={notLinkedSubtype} linkType={linkType} sortBy={sortBy} setLoading={setLoading} platforms={platformsToFilter} setPlatformsToFilter={setPlatformsToFilter} accountsToFilter={accountsToFilter} setShowCartTab={setShowCartTab} showCartTab={showCartTab} setProducts={setProducts}/> : <></>}
      {showAccountsTab ? <ConnectionsAccountsTab notLinkedSubtype={notLinkedSubtype} linkType={linkType} sortBy={sortBy} setLoading={setLoading} platformsToFilter={platformsToFilter} accountsToFilter={accountsToFilter} setAccountsToFilter={setAccountsToFilter} setProducts={setProducts} showAccountsTab={showAccountsTab} setShowAccountsTab={setShowAccountsTab}/> : <></>}
    </div>
  )
}
