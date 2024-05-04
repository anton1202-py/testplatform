import React, {useEffect, useState} from "react";
import "../../styles/connections.css"
import {analyticAPI} from "../../api";
import Checkbox from "react-custom-checkbox";
import Loader from "../Loader";

export const ConnectionsTable = ({
                                   loading,
                                   sortBy,
                                   setSortBy,
                                   products,
                                   productsToExport,
                                   setProductsToExport,
                                   setProducts,
                                   setLoading,
                                   accountsToFilter,
                                   platformsToFilter,
                                   linkType,
                                   notLinkedSubtype,
                                 }) => {
  const [checkboxes, setCheckboxes] = useState(new Map());
  const [ascendingMarketSort, setAscendingMarketSort] = useState(true)
  const [ascendingStockSort, setAscendingStockSort] = useState(true)


  const sortProducts = (sortBy) => {
    if (sortBy.includes("market")) {
      setAscendingMarketSort(prevState => !prevState)
    } else {
      setAscendingStockSort(prevState => (!prevState))
    }
    setSortBy(sortBy)
    setLoading(true)
    analyticAPI.get(`products/?connection__isnull=${linkType}&account__in=${accountsToFilter}&account__platform__platform_type__in=${notLinkedSubtype === "4" ? notLinkedSubtype :platformsToFilter}&sort_by=${sortBy}`).then(
      response => {
        setProducts(response.data.results)
      }
    ).catch(error => console.log(error)).finally(() => setLoading(false))
  }

  useEffect(() => {
    let checkboxes_initial = new Map();
    for (let product of products) {
      const marketPlaceProductId = product.other_marketplace?.id;
      const myStockProductId = product.moy_sklad?.id;

      if (marketPlaceProductId) {
        checkboxes_initial[marketPlaceProductId] = false;
      } else {
        checkboxes_initial[myStockProductId] = false;
      }
    }
    setCheckboxes(checkboxes_initial)
  }, [products])

  const handleCheckboxChange = (checkboxId) => {
    setCheckboxes(prevState => ({
      ...prevState,
      [checkboxId]: !prevState[checkboxId],
    }));
  };

  const handleMasterCheckboxChange = () => {
    const allChecked = Object.values(checkboxes).every(value => value);
    const updatedCheckboxes = {};
    for (const key in checkboxes) {
      updatedCheckboxes[key] = !allChecked;
    }
    const newProductToExport = new Set([...productsToExport]);
    if (!allChecked) {
      for (let product of products) {
        const marketPlaceProductId = product.other_marketplace?.id;
        const myStockProductId = product.moy_sklad?.id;
        if (marketPlaceProductId) {
          newProductToExport.add(marketPlaceProductId);
        }
        if (myStockProductId) {
          newProductToExport.add(myStockProductId);
        }
      }
      setProductsToExport(prevState => new Set([...prevState, ...newProductToExport]))
    } else {
      setProductsToExport(new Set())
    }
    setCheckboxes(updatedCheckboxes);
  };

  const updateProductsToExport = (product) => {
    const marketPlaceProductId = product.other_marketplace?.id;
    const myStockProductId = product.moy_sklad?.id;
    const newProductToExport = new Set([...productsToExport]);

    if (marketPlaceProductId) {
      handleCheckboxChange(marketPlaceProductId)
      if (newProductToExport.has(marketPlaceProductId)) {
        newProductToExport.delete(marketPlaceProductId);
      } else {
        newProductToExport.add(marketPlaceProductId);
      }
    }

    if (myStockProductId) {
      handleCheckboxChange(myStockProductId)
      if (newProductToExport.has(myStockProductId)) {
        newProductToExport.delete(myStockProductId);
      } else {
        newProductToExport.add(myStockProductId);
      }
    }
    setProductsToExport(prevState => new Set([...prevState, ...newProductToExport]))
  }

  const isChecked = (product) => {
    const marketPlaceProductId = product.other_marketplace?.id;
    const myStockProductId = product.moy_sklad?.id;

    if (marketPlaceProductId) {
      return checkboxes[marketPlaceProductId]
    }
    return checkboxes[myStockProductId]
  }

  const isMasterCheckboxChecked = () => {
    if (Object.keys(checkboxes).length === 0) {
      return false
    }

    return Object.values(checkboxes).every(value => value)
  }

  return (loading ? <Loader/> : (
      <table className="connection-table">
        <thead>
        <tr className="table-header">
          <td className="checkbox-col">
            <Checkbox className="custom-checkbox" checked={isMasterCheckboxChecked}
                      onChange={handleMasterCheckboxChange} icon={<img src="/images/checbox.svg" style={{width: "28px"}}
                                                                       alt=""/>}/>
          </td>
          <td className="table-header">
            <div className="table-header-item-container">
              <p>Наименование товара на маркетплейсе</p>
              <img className="arrow-up" src={ascendingMarketSort ? "/images/up_arrow.svg" : "/images/down_arrow.png"}
                   alt="" onClick={() => sortProducts(!ascendingMarketSort ? "market" : "-market")}/>
            </div>
          </td>
          <div className="right-side-header">
          <td className="table-header">
            <div className="table-header-item-container">
              <p>Наименование товара на "Мой склад"</p>
              <img className="arrow-up" src={ascendingStockSort ? "/images/up_arrow.svg" : "/images/down_arrow.png"}
                   alt="" onClick={() => sortProducts(!ascendingStockSort ? "moy_sklad" : "-moy_sklad")}/>
            </div>
          </td>
          <td className="table-header">
            <div className="table-header-item-container">
              <img className="update-button" src="/images/update.svg" alt="" onClick={() => sortProducts(sortBy)}/>
            </div>
          </td>
          </div>
        </tr>
        </thead>
        <tbody>
        {products.map((product) => (
          <tr>
            <td className="checkbox-col">
              <div className="table-header-item-container">
                <Checkbox onChange={() => updateProductsToExport(product)} checked={isChecked(product)}
                          className="custom-checkbox"
                          icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
              </div>
            </td>
            <td>
              <div className="product-container">
                <div className="top-row">
                  <p className="product-name">
                    {product.other_marketplace ? product.other_marketplace.name + " (" + product.other_marketplace["vendor"] + ")" : ""}
                  </p>
                </div>
                <div className="bottom-row">
                  <p className="product-bottom-info">
                    {product.other_marketplace ? "ску: " + product.other_marketplace.sku : ""}
                  </p>
                  <p className="product-bottom-info">
                    {product.other_marketplace ? "артикул: " + product.other_marketplace["vendor"] : ""}
                  </p>
                  <p className="product-bottom-info">
                    {product.other_marketplace ? "баркод: " + product.other_marketplace["barcode"] : ""}
                  </p>
                </div>
              </div>
            </td>
            <td>
              <div className="product-container">
                <div className="top-row">
                  <p className="product-name">
                    {product.moy_sklad ? product.moy_sklad.name + " (" + product.moy_sklad["vendor"] + ")" : ""}
                  </p>
                </div>
                <div className="bottom-row">
                  <p className="product-bottom-info">
                    {product.moy_sklad ? "товар-айди: " + product.moy_sklad.sku : ""}
                  </p>
                  <p className="product-bottom-info">
                    {product.moy_sklad ? "артикул: " + product.moy_sklad["vendor"] : ""}
                  </p>
                  <p className="product-bottom-info">
                    {product.moy_sklad ? "баркод: " + product.moy_sklad["barcode"] : ""}
                  </p>
                </div>
              </div>
            </td>
          </tr>
        ))}
        </tbody>
      </table>
    )
  )
}
