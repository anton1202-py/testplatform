import React from "react";
import "../styles/connections.css"

export const StocksHeader = ({orderType, setOrderType}) => {
  const onOrderTypeChange = (order) => {
    setOrderType(order)
  }

  return (
    <div className="filters-container">
      <div className="filters">
        <div className={orderType === "" ? "filter-label" : ""} onClick={() => onOrderTypeChange("")}>
          <p className={orderType === "" ? "selected-filter" : "filter"}>Все 24</p>
        </div>
        <div className={orderType === "0" ? "filter-label" : ""} onClick={() => onOrderTypeChange("0")}>
          <p className={orderType === "0" ? "selected-filter" : "filter"}>Срочные 24</p>
        </div>
        <div className={orderType === "1" ? "filter-label" : ""} onClick={() => onOrderTypeChange("1")}>
          <p className={orderType === "1" ? "selected-filter" : "filter"}>Сегодня 24</p>
        </div>
        <div className={orderType === "2" ? "filter-label" : ""} onClick={() => onOrderTypeChange("2")}>
          <p className={orderType === "2" ? "selected-filter" : "filter"}>Остальные 24</p>
        </div>
      </div>
    </div>
  )
}
