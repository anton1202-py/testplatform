import React, {useState} from "react";
import "../../styles/connections.css"
import {analyticAPI} from "../../api";

export const ConnectionsHeader = ({
                                    linkType,
                                    sortBy,
                                    setLinkType,
                                    setLoading,
                                    setProducts,
                                    platformsToFilter,
                                    accountsToFilter,
                                    setNotLinkedSubtype,
                                    notLinkedSubtype
                                  }) => {

  const [linked, setLinked] = useState(false)

  const filterProducts = (link, notLinked) => {
    if (link === "1") {
      setLinked(true)
    } else {
      setLinked(false)
    }
    setNotLinkedSubtype(notLinked)
    setLinkType(link)
    setLoading(true)
    analyticAPI.get(`products/?connection__isnull=${link}&account__platform__platform_type__in=${notLinked === "4" ? notLinked : platformsToFilter}&account__in=${accountsToFilter}&sort_by=${sortBy}`).then(
      response => {
        setProducts(response.data.results)
      }
    ).catch(error => console.log(error)).finally(() => setLoading(false))
  }

  return (
    <div className="filters-container">
      <div className="filters">
        <div className={linkType === "" ? "filter-label" : ""} onClick={() => filterProducts("")}>
          <p className={linkType === "" ? "selected-filter" : "filter"}>Все товары</p>
        </div>
        <div className={linkType === "0" ? "filter-label" : ""} onClick={() => filterProducts("0")}>
          <p className={linkType === "0" ? "selected-filter" : "filter"}>Связанные товары</p>
        </div>
        <div className={linkType === "1" ? "filter-label" : ""} onClick={() => filterProducts("1")}>
          <p className={linkType === "1" ? "selected-filter" : "filter"}>Без связи</p>
        </div>
      </div>
      {
        linked && (
          <div className="second-filters">
            <div className={notLinkedSubtype === "0, 1, 2, 3" ? "filter-label" : ""} onClick={() => filterProducts("1", "0, 1, 2, 3")}>
              <p className={notLinkedSubtype === "0, 1, 2, 3" ? "selected-filter" : "filter"}>На маркетплейсе</p>
            </div>
            <div className={notLinkedSubtype === "4" ? "filter-label" : ""} onClick={() => filterProducts("1", "4")}>
              <p className={notLinkedSubtype === "4" ? "selected-filter" : "filter"}>На "Мой Склад"</p>
            </div>
          </div>
        )
      }
    </div>
  )

}
