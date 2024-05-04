import React, {useEffect, useState} from "react";
import "../../styles/connections.css"
import {analyticAPI} from "../../api";
import Checkbox from "react-custom-checkbox";

export const ConnectionsCartTab = ({ notLinkedSubtype, linkType, sortBy, platforms, setPlatformsToFilter, accountsToFilter, showCartTab, setShowCartTab, setProducts}) =>{
  const [marketPlaces, setMarketPlaces] = useState([])

  useEffect(()=> {
    analyticAPI.get("marketplace-types/").then(
      response => setMarketPlaces(response.data)
    )
  }, [])

  const filterProducts = (platformIdx) => {
    let platformsToFilter = [...platforms]
    if (!platformsToFilter.includes(platformIdx)){
      platformsToFilter.push(platformIdx)
    } else {
      platformsToFilter = platforms.filter(currentPlatform => currentPlatform !== platformIdx)
    }
    setPlatformsToFilter(platformsToFilter)
    analyticAPI.get(`products/?connection__isnull=${linkType}&account__platform__platform_type__in=${notLinkedSubtype === "4" ? notLinkedSubtype :platformsToFilter}&account__in=${accountsToFilter}&sort_by=${sortBy}`).then(
      response => {
        setProducts(response.data.results)
      }
    ).catch(error => console.log(error))
  }

  return (
    <div className="shops">
      <div className="shops-content">
        <div className="shops-header">
          <p className="shops-header-text">Маркетплейсы</p>
          <img className="shops-header-cross" src="/images/cross.svg" alt="" onClick={() => setShowCartTab(!showCartTab)}/>
        </div>
        {marketPlaces.map((marketPlace, idx) => (
            <div className="cart">
              <div className="table-header-item-container checkbox-col" key={marketPlace}>
                <Checkbox onChange={() => filterProducts(idx)} className="custom-checkbox" icon={<img src="/images/checbox.svg" style={{width: "28px"}}
                                                                                                      alt=""/>}/>
                <p className="checkbox-label">{marketPlace}</p>
              </div>
            </div>)
        )
        }
      </div>
    </div>
  )
}
