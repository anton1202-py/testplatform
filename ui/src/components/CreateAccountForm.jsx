import "../styles/accounts.css"
import React, {useEffect, useState} from "react";
import Select from 'react-select';
import {analyticAPI} from "../api";

const options = [
  {value: 'link', label: 'Связь'},
  {value: 'account', label: 'Магазин'},
  {value: 'stock', label: 'Мой Склад'},
];

export const CreateAccountForm = ({onClose}) => {
  const [objectType, setObjectType] = useState({value: 'account', label: 'Магазин'})
  const [marketplaces, setMarketplaces] = useState()
  const [marketplacesProducts, setMarketplacesProducts] = useState()
  const [myWarehouseProducts, setMyWarehouseProducts] = useState()
  const [marketPlace, setMarketPlace] = useState()
  const [accountMarketPlace, setAccountMarketPlace] = useState()
  const [marketPlaceProduct, setMarketPlaceProduct] = useState()
  const [myWarehouseProduct, setMyWarehouseProduct] = useState()
  const [marketplaceAuthFields, setMarketplaceAuthFields] = useState({})
  const [accountName, setAccountName] = useState("")
  const [accountAuthData, setAccountAuthData] = useState({})

  const handleMarketplaceChange = (value) => {
    analyticAPI.get(`products/?account__platform__platform_type=${value.value}&no-comparsion=1&only-no-connections=1`).then(
      response => {
        setMarketplacesProducts(response.data.results.map((marketplace_product) => (
          {value: marketplace_product.id, label: marketplace_product.name}
        )))
        setMarketPlace(value);
      }
    )
  };

  useEffect(() => {
    if (objectType.value === "stock") {
      const stockValue = {value: "4", label: "Мой Склад"}
      setAccountMarketPlace(stockValue)
      onSelectAccountPlatform(stockValue)
    }
  }, [objectType])

  useEffect(() => {
    analyticAPI.get(`marketplace-types/`).then(
      response => {
        setMarketplaces(response.data.map((marketplace_type, idx) => ({value: idx, label: marketplace_type})))
      }
    )
    analyticAPI.get(`products/?account__platform__platform_type=4&no-comparsion=1&only-no-connections=1`).then(
      response => {
        setMyWarehouseProducts(response.data.results.map((marketplace_product) => (
          {value: marketplace_product.id, label: marketplace_product.name}
        )))
      }
    )
  }, [])

  const createLink = () => {
    if (!marketPlaceProduct || !myWarehouseProduct) return;
    let requestData = {
      other_marketplace_product: marketPlaceProduct["value"],
      moy_sklad_product: myWarehouseProduct["value"]
    }
    analyticAPI.post(
      'create-manual-connection/',
      requestData
    ).then(
      response => {
        console.log(response)
        onClose()
      }
    ).catch(error => console.log(error))

  }

  const onSelectAccountPlatform = (value) => {
    analyticAPI.get(`platform-auth-fields/${value.value}/`).then(
      response => {
        setMarketplaceAuthFields(response.data)
        setAccountMarketPlace(value)
      }
    )
  }

  const createAccount = (value) => {
    if (!accountMarketPlace || !accountName || !accountAuthData) return;
    let requestData = {
      "platform_type": accountMarketPlace["value"],
      "name": accountName,
      "authorization_fields": accountAuthData
    }
    analyticAPI.post(
      'create-account/',
      requestData
    ).then(
      response => {
        console.log(response)
        onClose()
      }
    ).catch(error => console.log(error))
  }

  const onAuthFieldChange = (event) => {
    let auth_data = accountAuthData
    auth_data[event.target.name] = event.target.value
    setAccountAuthData(auth_data)
  }


  const onObjectTypeChange = (event) => {
    setObjectType(event)
    setAccountMarketPlace(null)
    setMarketplaceAuthFields({})
  }


  return (
    <div className="create-account-area">
      <div className="create-account-header">
        <p className="create-account-title">Создать</p>
        <img src="/images/cross.svg" alt="" onClick={onClose} className="cross-img"/>
      </div>
      <div>
        <p className="label-text">Тип объекта</p>
        <Select
          defaultValue={objectType}
          onChange={onObjectTypeChange}
          options={options}
          className="react-select-container"
          classNamePrefix="react-select"
        />
      </div>
      {objectType.value === "link" ? (
        <div className="creation-fields">
          <div className="creation-field">
            <p className="label-text">Выбор маркетплейса</p>
            <Select
              defaultValue={marketPlace}
              onChange={handleMarketplaceChange}
              options={marketplaces}
              className="react-select-container"
              classNamePrefix="react-select"
            />
          </div>
          <div className="creation-field">
            <p className="label-text">Товар</p>
            <Select
              defaultValue={marketPlaceProduct}
              onChange={setMarketPlaceProduct}
              options={marketplacesProducts}
              isDisabled={!marketPlace}
              className="react-select-container"
              classNamePrefix="react-select"
            />
          </div>
          <div className="creation-field">
            <p className="label-text">Товар на моем складе</p>
            <Select
              defaultValue={myWarehouseProduct}
              onChange={setMyWarehouseProduct}
              options={myWarehouseProducts}
              isDisabled={!marketPlace}
              className="react-select-container"
              classNamePrefix="react-select"
            />
          </div>
        </div>
      ) : (
        objectType.value === "account" ? (
            <div className="creation-fields">
              <div className="creation-field">
                <p className="label-text">Название</p>
                <input
                  type="text"
                  className="field text-icon"
                  value={accountName}
                  onChange={e => setAccountName(e.target.value)}
                />
              </div>
              <div className="creation-field">
                <p className="label-text">Маркетплейс</p>
                <Select
                  defaultValue={accountMarketPlace}
                  onChange={onSelectAccountPlatform}
                  options={marketplaces}
                  className="react-select-container"
                  classNamePrefix="react-select"
                />
              </div>
              {
                Object.keys(marketplaceAuthFields).map((key, index) => (
                  <div key={`group-input-${index}`} className="custom-fields">
                    <p className="label-text">{marketplaceAuthFields[key].name}</p>
                    <input type={marketplaceAuthFields[key].type} onChange={onAuthFieldChange} name={key}
                           className="field text-icon"/>
                  </div>
                ))
              }
            </div>
          ) :
          (
            <div className="creation-fields">
              <div className="creation-field">
                <p className="label-text">Название</p>
                <input
                  type="text"
                  className="field text-icon"
                  value={accountName}
                  onChange={e => setAccountName(e.target.value)}
                />
              </div>
              {
                Object.keys(marketplaceAuthFields).map((key, index) => (
                  <div key={`group-input-${index}`} className="custom-fields">
                    <p className="label-text">{marketplaceAuthFields[key].name}</p>
                    <input type={marketplaceAuthFields[key].type} onChange={onAuthFieldChange} name={key}
                           className="field text-icon"/>
                  </div>
                ))
              }
            </div>
          )
      )}
      <div className="modal-buttons">
        <button type="button" onClick={onClose} className="btn btn-negative"><p>Отмена</p></button>
        {objectType.value === "link" ?
          <button type="button" className="btn btn-primary" onClick={createLink}><p>Создать связь</p></button>
          :
          <button type="button" className="btn btn-primary" onClick={createAccount}><p>Добавить магазин</p></button>
        }
      </div>
    </div>
  )
}
