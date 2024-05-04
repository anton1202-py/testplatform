import {useEffect, useState} from "react";
import {analyticAPI} from "../../api";
import React from "react";
import Checkbox from "react-custom-checkbox";

export const OrdersAccountsTab = ({sortBy, platformsToFilter, accountsToFilter, setAccountsToFilter, setOrdersItems, showAccountsTab, setShowAccountsTab, ordersType}) => {
  const [accounts, setAccounts] = useState([])

  const filterProducts = (accountId) => {
    let newAccountsToFilter = [...accountsToFilter]
    if (!accountsToFilter.includes(accountId)){
      newAccountsToFilter.push(accountId)
    } else {
      newAccountsToFilter = newAccountsToFilter.filter(id => id !== accountId)
    }
    setAccountsToFilter(newAccountsToFilter)
    analyticAPI.get(`order-items/?orders_type=${ordersType}&order__account__in=${newAccountsToFilter}&sort_by=${sortBy}&order__account__platform__platform_type__in=${platformsToFilter}`).then(
      response => {
        setOrdersItems(response.data.results)
      }
    ).catch(error => console.log(error))
  }

  useEffect(()=> {
    analyticAPI.get("accounts/").then(
      response => setAccounts(response.data.results)
    ).catch(error => console.log(error))
  }, [])

  return (
    <div className="shops">
      <div className="shops-content">
        <div className="shops-header">
          <p className="shops-header-text">Магазины</p>
          <img className="shops-header-cross" src="/images/cross.svg" alt="" onClick={() => setShowAccountsTab(!showAccountsTab)}/>
        </div>
        {
          accounts.map((account) => (
            <div className="cart">
                <div className="table-header-item-container checkbox-col" key={account.id}>
                  <Checkbox onChange={() => filterProducts(account.id)} className="custom-checkbox" icon={<img src="/images/checbox.svg" style={{width: "28px"}}
                                                                                                               alt=""/>}/>
                  <p className="checkbox-label">{account.name}</p>
              </div>
            </div>
          )
          )
        }
      </div>
    </div>
  )
}
