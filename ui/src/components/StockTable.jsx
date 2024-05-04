import React from "react";
import Checkbox from "react-custom-checkbox";


export const StockTable = () => {
  return (
    <table className="stock-table">
      <thead>
      <tr className="table-header">
        <td style={{minWidth: "56px"}}></td>
        <td className="table-header">№ заказа</td>
        <td className="table-header">МП</td>
        <td className="table-header">Наименование</td>
        <td className="table-header">
          <div className="table-header-item-container">
            <p>Бренд</p>
            <img className="arrow-up" src="/images/filter.svg"
                 alt=""/>
          </div>
        </td>
        <td className="table-header">Количество штук</td>
        <td className="table-header">Баркод</td>
        <td className="table-header">
          <div className="table-header-item-container">
            <p>Дата и время поступления</p>
            <img className="arrow-up" src="/images/filter.svg"
                 alt=""/>
          </div>
        </td>
        <td className="table-header">
          <div className="table-header-item-container">
            <p>Дата и время отгрузки</p>
            <img className="arrow-up" src="/images/filter.svg"
                 alt=""/>
          </div>
        </td>
      </tr>
      </thead>
      <tbody>
      <tr>
        <td className="checkbox-col">
          <div className="table-header-item-container">
            <Checkbox
              className="custom-checkbox"
              icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
          </div>
        </td>
        <td>Абонементы на тарифы «Мегафон Kids»</td>
        <td>M</td>
        <td>"Dayzy"</td>
        <td>2шт</td>
        <td>2037707052122</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
      </tr>
      <tr>
        <td className="checkbox-col">
          <div className="table-header-item-container">
            <Checkbox
              className="custom-checkbox"
              icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
          </div>
        </td>
        <td>Абонементы на тарифы «Мегафон Kids»</td>
        <td>M</td>
        <td>"Dayzy"</td>
        <td>2шт</td>
        <td>2037707052122</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
      </tr>
      <tr>
        <td className="checkbox-col">
          <div className="table-header-item-container">
            <Checkbox
              className="custom-checkbox"
              icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
          </div>
        </td>
        <td>Абонементы на тарифы «Мегафон Kids»</td>
        <td>M</td>
        <td>"Dayzy"</td>
        <td>2шт</td>
        <td>2037707052122</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
      </tr>
      <tr>
        <td className="checkbox-col">
          <div className="table-header-item-container">
            <Checkbox
              className="custom-checkbox"
              icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
          </div>
        </td>
        <td>Абонементы на тарифы «Мегафон Kids»</td>
        <td>M</td>
        <td>"Dayzy"</td>
        <td>2шт</td>
        <td>2037707052122</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
      </tr>
      <tr>
        <td className="checkbox-col">
          <div className="table-header-item-container">
            <Checkbox
              className="custom-checkbox"
              icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
          </div>
        </td>
        <td>Абонементы на тарифы «Мегафон Kids»</td>
        <td>M</td>
        <td>"Dayzy"</td>
        <td>2шт</td>
        <td>2037707052122</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
      </tr>
      <tr>
        <td className="checkbox-col">
          <div className="table-header-item-container">
            <Checkbox
              className="custom-checkbox"
              icon={<img src="/images/checbox.svg" style={{width: "28px"}} alt=""/>}/>
          </div>
        </td>
        <td>Абонементы на тарифы «Мегафон Kids»</td>
        <td>M</td>
        <td>"Dayzy"</td>
        <td>2шт</td>
        <td>2037707052122</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
        <td>11.09.23</td>
      </tr>
      </tbody>
    </table>
  )
}
