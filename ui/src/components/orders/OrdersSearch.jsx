import React, {useState} from "react";
import {analyticAPI} from "../../api";


export const OrdersSearch = ({setOrdersItems, platformsToFilter, accountsToFilter, ordersType}) =>{
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchVisible, setIsSearchVisible] = useState(false);

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value)
    analyticAPI.get(`order-items/?orders_type=${ordersType}&order__account__platform__platform_type__in=${platformsToFilter}&order__account__in=${accountsToFilter}&search=${e.target.value}`).then(
      response => setOrdersItems(response.data.results)
    ).catch(error => console.log(error))
  }

  const onSearchClick = (event) => {
    if (event.target.className !== "search-input") setIsSearchVisible(!isSearchVisible);
  }

  return (
    <>
      <div  onClick={onSearchClick} className="btn btn-negative search-input-container">
        <img src="/images/search.svg" width="24px" height="24px" alt=""
            />
        {isSearchVisible &&
          <input
            type="text"
            className="search-input"
            placeholder="Поиск"
            value={searchQuery}
            onChange={handleSearchChange}
          />
        }
        {isSearchVisible &&
          <img src="/images/cross.svg" width="16px" height="16px" alt=""
               onClick={() => setIsSearchVisible(!isSearchVisible)}/>
        }
      </div>
    </>
  )
}
