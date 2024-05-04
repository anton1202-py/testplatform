import React, {useEffect, useState} from "react";
import "../styles/connections.css"
import {ConnectionsTable} from "../components/connections/ConnectionsTable";
import {ConnectionsTabs} from "../components/connections/ConnectionsTabs";
import {analyticAPI} from "../api";
import {useAuth} from "../components/AuthProvider";
import {ConnectionsHeader} from "../components/connections/ConnectionsHeader";
import {ConnectionsSearch} from "../components/connections/ConnectionsSearch";
import Modal from "../components/Modal";
import {CreateAccountForm} from "../components/CreateAccountForm";

export const ConnectionsPage = () => {
  const [showAccountsTab, setShowAccountsTab] = useState(false);
  const [showCartTab, setShowCartTab] = useState(false);
  const [products, setProducts] = useState([]);
  const [accountsToFilter, setAccountsToFilter] = useState([]);
  const [platformsToFilter, setPlatformsToFilter] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [productsToExport, setProductsToExport] = useState(new Set());
  const [sortBy, setSortBy] = useState("market")
  const [linkType, setLinkType] = useState("")
  const [notLinkedSubtype, setNotLinkedSubtype] = useState("")


  const openModal = () => {
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  const exportReport = () => {
    analyticAPI.post("export-report/", {
      products: [...productsToExport]
    }, {
        responseType: 'blob'
      }).then(
      response => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const currentDate = new Date();
        const formattedDate = currentDate.toISOString().slice(0, 19).replace(/[:T]/g, '-');

        const fileName = `Отчет-${formattedDate}.xlsx`;
        const link = document.createElement('a');

        link.href = url;
        link.setAttribute('download', fileName); // Set the file name
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
      }
    )
  }

  const {login} = useAuth()

  useEffect(()=>{
    if (login){
      setLoading(true)
      analyticAPI.get(`products/`).then(
        response => {
          setProducts(response.data.results)
        }
        ).catch(error => console.log(error)).finally(() => setLoading(false))
    }

  }, [login])

  return (
    <>
      <div className="connection-page">
        <img
          alt=""
          src="/images/page-bkg.svg"
          className="main-background-image"
        />
        <div className="content-area">
          <h1 className="page-title">Связи</h1>
          <div className="header">
            <ConnectionsHeader notLinkedSubtype={notLinkedSubtype} setNotLinkedSubtype={setNotLinkedSubtype} linkType={linkType} setLinkType={setLinkType} setLoading={setLoading} setProducts={setProducts} accountsToFilter={accountsToFilter}  platformsToFilter={platformsToFilter} sortBy={sortBy}/>
            <div className="controlls">
              <ConnectionsSearch setProducts={setProducts} accountsToFilter={accountsToFilter} platformsToFilter={platformsToFilter}/>
              <div className={"btn btn-negative search-input-container" + (showAccountsTab ? " active" : "")} onClick={() => setShowAccountsTab(!showAccountsTab)}>
                <svg width="24" height="24" viewBox="0 0 22 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M21 7.4998H16.21L11.82 0.929805C11.42 0.339805 10.55 0.339805 10.16 0.929805L5.77 7.4998H1C0.45 7.4998 0 7.9498 0 8.4998C0 8.5898 0.00999996 8.6798 0.04 8.7698L2.58 18.0398C2.81 18.8798 3.58 19.4998 4.5 19.4998H17.5C18.42 19.4998 19.19 18.8798 19.43 18.0398L21.97 8.7698L22 8.4998C22 7.9498 21.55 7.4998 21 7.4998ZM10.99 3.2898L13.8 7.4998H8.18L10.99 3.2898ZM11 15.4998C9.9 15.4998 9 14.5998 9 13.4998C9 12.3998 9.9 11.4998 11 11.4998C12.1 11.4998 13 12.3998 13 13.4998C13 14.5998 12.1 15.4998 11 15.4998Z"
                    fill="#45475D"/>
                </svg>
              </div>
              <div className={"btn btn-negative search-input-container" + (showCartTab ? " active" : "")}
                   onClick={() => setShowCartTab(!showCartTab)}>
                <svg width="24" height="24" viewBox="0 0 20 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M6 16.5C4.9 16.5 4.01 17.4 4.01 18.5C4.01 19.6 4.9 20.5 6 20.5C7.1 20.5 8 19.6 8 18.5C8 17.4 7.1 16.5 6 16.5ZM0 1.5C0 2.05 0.45 2.5 1 2.5H2L5.6 10.09L4.25 12.53C3.52 13.87 4.48 15.5 6 15.5H17C17.55 15.5 18 15.05 18 14.5C18 13.95 17.55 13.5 17 13.5H6L7.1 11.5H14.55C15.3 11.5 15.96 11.09 16.3 10.47L19.88 3.98C20.25 3.32 19.77 2.5 19.01 2.5H4.21L3.54 1.07C3.38 0.72 3.02 0.5 2.64 0.5H1C0.45 0.5 0 0.95 0 1.5ZM16 16.5C14.9 16.5 14.01 17.4 14.01 18.5C14.01 19.6 14.9 20.5 16 20.5C17.1 20.5 18 19.6 18 18.5C18 17.4 17.1 16.5 16 16.5Z"
                    fill="#45475D"/>
                </svg>
              </div>
              <div className="btn btn-negative search-input-container" onClick={exportReport}>
                <img id="doc" className="" width="24px" height="24px" src="/images/doc.svg" alt=""/>
              </div>
              <button onClick={openModal} style={{"height": "39px"}} className="btn btn-primary"><p>Создать</p></button>
            </div>
          </div>
          <ConnectionsTable notLinkedSubtype={notLinkedSubtype} sortBy={sortBy} setSortBy={setSortBy} products={products} productsToExport={productsToExport}
                                                   setProductsToExport={setProductsToExport} setProducts={setProducts}
                                                   setLoading={setLoading} loading={loading} accountsToFilter={accountsToFilter} platformsToFilter={platformsToFilter} linkType={linkType}/>
          <Modal isOpen={isModalOpen}>
            <CreateAccountForm onClose={closeModal}/>
          </Modal>
        </div>
        {
          !showCartTab && !showAccountsTab ? (
            <></>
          ) : <ConnectionsTabs notLinkedSubtype={notLinkedSubtype} linkType={linkType} sortBy={sortBy} setLoading={setLoading} platformsToFilter={platformsToFilter} setPlatformsToFilter={setPlatformsToFilter} accountsToFilter={accountsToFilter} setAccountsToFilter={setAccountsToFilter} showCartTab={showCartTab} showAccountsTab={showAccountsTab} setProducts={setProducts} setShowCartTab={setShowCartTab} setShowAccountsTab={setShowAccountsTab}/>
        }
      </div>
    </>
  )
}
