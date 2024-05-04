import React, {useEffect, useState} from "react";
import "../../styles/connections.css"
import {analyticAPI} from "../../api";
import Checkbox from "react-custom-checkbox";
import Loader from "../Loader";

export const OrdersTable = ({
                                   loading,
                                   sortBy,
                                   setSortBy,
                                   ordersItems,
                                   setOrdersItems,
                                   setLoading,
                                   accountsToFilter,
                                   platformsToFilter,
                                   ordersType
                                 }) => {


  const sortProducts = (sortBy) => {
    setSortBy(sortBy)
    setLoading(true)
    analyticAPI.get(`order-items/?orders_type=${ordersType}&order__account__in=${accountsToFilter}&order__account__platform__platform_type__in=${platformsToFilter}&sort_by=${sortBy}`).then(
      response => {
        setOrdersItems(response.data.results)
      }
    ).catch(error => console.log(error)).finally(() => setLoading(false))
  }

  return (loading ? <Loader/> : (
      <table className="orders-table">
        <thead>
        <tr className="table-header">
          <th></th>
          <th><div className="th-content"><p>№ заказа</p></div></th>
          <th><div className="th-content"><p>Маркетплейс</p></div></th>
          <th><div className="th-content"><p>Наименование</p></div></th>
          <th><div className="th-content"><p>Бренд</p><img id="doc" className="" width="16px" height="16px" src="/images/filter_sign.svg" alt=""/></div></th>
          <th><div className="th-content"><p>Количество штук</p></div></th>
          <th><div className="th-content"><p>Баркод</p></div></th>
          <th><div className="th-content"><p>Дата и время поступления</p><img id="doc" className="" width="16px" height="16px"
                                                                              src="/images/filter_sign.svg" alt=""/></div></th>
          <th><div className="th-content"><p>Дата и время отгрузки</p><img id="doc" className="" width="16px" height="16px"
                                                                           src="/images/filter_sign.svg" alt=""/></div></th>
          <th><div className="th-content"><p>Статус</p><img id="doc" className="" width="16px" height="16px"
                                                            src="/images/filter_sign.svg" alt=""/></div></th>
          <th><div className="th-content"><p>Лист отгрузки</p></div></th>
          <th><div className="th-content"><p>Этикетки</p></div></th>
        </tr>
        </thead>
        <tbody>
        {ordersItems.map((orderItem) => (
          <tr>
            <td className="checkbox-col">
              <div className="table-header-item-container">
                <Checkbox
                  className="custom-checkbox"
                  icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
              </div>
            </td>
            <td>
              <p>{orderItem.order_number}</p>
            </td>
            <td>
              <p>{orderItem.platform_name}</p>
            </td>
            <td>
              <p>{orderItem.product_name}</p>
            </td>
            <td>
              <p>{orderItem.product_brand ? orderItem.product_brand : "-"}</p>
            </td>
            <td>
              <p>{orderItem.quantity ? orderItem.quantity : "0"} шт</p>
            </td>
            <td>
              <p>{orderItem.product_barcode}</p>
            </td>
            <td>
              <p>{orderItem.created_dt}</p>
            </td>
            <td>
              <p>{orderItem.shipped_dt ? orderItem.shipped_dt : "-"}</p>
            </td>
            <td>
              <div className="status-container">
                <div className="status-circle" style={{background: orderItem.order_status_color}}></div>
                <p>{orderItem.order_status_name}</p>
              </div>
            </td>
            <td>
              <p>{orderItem.price} ₽</p>
            </td>
            <td>
              <a>Этикетка</a>
            </td>
          </tr>
        ))}
        </tbody>
      </table>
    )
  )
}
