import React, {useState} from "react";
import "../../styles/connections.css"
import {analyticAPI} from "../../api";

export const OrdersHeader = ({
                                    ordersType,
                                    counts,
                                    sortBy,
                                    setOrdersType,
                                    setLoading,
                                    platformsToFilter,
                                    accountsToFilter,
                                    setOrdersItems
                                  }) => {

  const [linked, setLinked] = useState(false)

  const filterOrders = (link, notLinked) => {
    if (link === "1") {
      setLinked(true)
    } else {
      setLinked(false)
    }
    setOrdersType(link)
    setLoading(true)
    analyticAPI.get(`order-items/?orders_type=${link}&order__account__platform__platform_type__in=${platformsToFilter}&order__account__in=${accountsToFilter}&sort_by=${sortBy}`).then(
      response => {
        setOrdersItems(response.data.results)
      }
    ).catch(error => console.log(error)).finally(() => setLoading(false))
  }

  return (
    <div className="filters-container">
      <div className="filters">
        <div className={ordersType === "" ? "filter-label" : ""} onClick={() => filterOrders("")}>
          <p className={ordersType === "" ? "selected-filter" : "filter"}>Все <span className="text-red">{counts["all"]}</span></p>
        </div>
        <div className={ordersType === "0" ? "filter-label" : ""} onClick={() => filterOrders("0")}>
          <p className={ordersType === "0" ? "selected-filter" : "filter"}>Срочные <span className="text-red">{counts["urgent"]}</span></p>
        </div>
        <div className={ordersType === "1" ? "filter-label" : ""} onClick={() => filterOrders("1")}>
          <p className={ordersType === "1" ? "selected-filter" : "filter"}>Сегодня <span className="text-red">{counts["today"]}</span></p>
        </div>
        <div className={ordersType === "2" ? "filter-label" : ""} onClick={() => filterOrders("2")}>
          <p className={ordersType === "2" ? "selected-filter" : "filter"}>Остальные <span className="text-red">{counts["other"]}</span></p>
        </div>
      </div>
    </div>
  )

}
