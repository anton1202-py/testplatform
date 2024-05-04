import React, {useEffect, useRef, useState} from 'react';
import Checkbox from "react-custom-checkbox";

import "../styles/login.css"
import {analyticAPI} from "../api";
import {useHistory} from "react-router-dom";
import { useAuth } from "./AuthProvider";
import {NotificationManager} from 'react-notifications';
import 'react-notifications/lib/notifications.css';

const LoginForm = () => {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [authContainerWidth, setAuthContainerWidth] = useState();
  const [authContainerHeight, setAuthContainerHeight] = useState();
  const history = useHistory();
  const {setToken, setLogin} = useAuth()

  const observedDiv = useRef(null);

  let createNotification = (type, message, timeout=3000) => {
    return () => {
      // eslint-disable-next-line default-case
      switch (type) {
        case 'info':
          NotificationManager.info(message, timeout);
          break;
        case 'success':
          NotificationManager.success(message, timeout);
          break;
        case 'warning':
          NotificationManager.warning(message, timeout);
          break;
        case 'error':
          NotificationManager.error(message, timeout);
          break;
      }
    };
  };

  useEffect(() => {
      if (!observedDiv.current) {
        // we do not initialize the observer unless the ref has
        // been assigned
        return;
      }

      // we also instantiate the resizeObserver and we pass
      // the event handler to the constructor
      const resizeObserver = new ResizeObserver(() => {
        if(observedDiv.current.offsetWidth !== authContainerWidth) {
          setAuthContainerWidth(observedDiv.current.offsetWidth);
        }
        if(observedDiv.current.offsetHeight !== authContainerHeight) {
          setAuthContainerHeight(observedDiv.current.offsetHeight);
        }
        console.log(authContainerWidth, authContainerHeight)
      });

      // the code in useEffect will be executed when the component
      // has mounted, so we are certain observedDiv.current will contain
      // the div we want to observe
      resizeObserver.observe(observedDiv.current);


      // if useEffect returns a function, it is called right before the
      // component unmounts, so it is the right place to stop observing
      // the div
      return function cleanup() {
        resizeObserver.disconnect();
      }
    },
    // only update the effect if the ref element changed
    )

  const login = () => {
    analyticAPI.post(
      "token/", {username:username, password: password}
    ).then(
      response=> {
        setToken(response.data.token)
        setLogin(username)
        history.push("/")
      }
    ).catch(
      error=>{
        let response_data = error.response.data
        for (const [key, value] of Object.entries(response_data)) {
          for (let i = 0; i < value.length; i++) {
            console.log(value[i])
            NotificationManager.error(value[i], 'Ошибка!', 4000);
          }
        }
      }
    )

  }

  return(
    <>
      <div className="login-area" >
        <div className="login-window-wrapper" ref={observedDiv}>
          <img
            alt=""
            className="background-image"
            src="/images/login-background-frame.png"
            style={{
              width: authContainerWidth,
              height: authContainerHeight,
              maxWidth: authContainerWidth,
              maxHeight: authContainerHeight
            }}
          />
          <img
            alt=""
            className="login-small-pipe"
            src="/images/login-lines/login-small-pipe.svg"
          />
          <div className="documents-buttons">
            <div className="document-button user-agreement-button">
              <img
                alt=""
                src="/images/user-agreement.svg"
                className="document-img"
              />
              <p className="document-text">Пользовательское соглашение</p>
            </div>
            <div className="document-button license-agreement-button">
              <img
                alt=""
                src="/images/license-agreement.svg"
                className="document-img"
              />
              <p className="document-text">Лицензионное соглашение</p>
            </div>
          </div>
          <div className="middle-bubble bubble-ssq-1">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-1"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-2">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-2"
              src="/images/sliding_squares/small_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-3">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-3"
              src="/images/sliding_squares/big_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-4">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-4"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-6">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-6"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-6-1">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-6-1"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-7">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-7"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-9">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-9"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-10">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-10"
              src="/images/sliding_squares/small_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-11">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-11"
              src="/images/sliding_squares/big_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-12">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-12"
              src="/images/sliding_squares/big_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-13">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-13"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-14">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-14"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-15">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-15"
              src="/images/sliding_squares/small_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="middle-bubble bubble-ssq-16">
            <img
              alt=""
              className="jopka-left"
              src="/images/sliding_squares/jopka_left.svg"
            />
            <img
              alt=""
              className="ssq-16"
              src="/images/sliding_squares/middle_size.png"
            />
            <img
              alt=""
              className="jopka-right"
              src="/images/sliding_squares/jopka_right.svg"
            />
          </div>
          <div className="login-window">
            <img
              alt=""
              src="/images/login-lines/upper-curve.png"
              className="login-upper-curve"
            />
            <img
              alt=""
              src="/images/login-lines/upper-pipe.png"
              className="login-upper-pipe"
            />
            <img
              alt=""
              src="/images/login-lines/bottom-curve.png"
              className="login-bottom-curve"
            />
            <img
              alt=""
              src="/images/login-lines/bottom-pipe.png"
              className="login-bottom-pipe"
            />
            <div className="window-background"></div>
            <div className="logo">
              <img
                alt=""
                className="logo-image"
                src="/images/login_logo.png"
              />
            </div>
            <div className="frame-5521">
              <div className="frame-5507">
                <div className="input-container">
                  <p className="label-text">Логин</p>
                  <input
                    type="text"
                    className="field text-icon"
                    name="username"
                    placeholder="Введите почту"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="input-container password-container">
                  <p className="label-text">Пароль</p>
                  <input
                    id="password-input"
                    type={passwordVisible ? "text" : "password"}
                    name="password"
                    className="field text-icon"
                    placeholder="Введите пароль"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <div className="eye-icon" onClick={() => setPasswordVisible(!passwordVisible)}>
                    <img
                      id="eye-icon"
                      alt="hide password"
                      className="eye-off-24"
                      src={passwordVisible ? "/images/opened-eye.png" : "/images/pass_hidden.svg"}
                    />
                  </div>
                </div>
                <div className="frame-5520">
                  <div className="table-header-item-container checkbox-col">
                    <Checkbox className="custom-checkbox" icon={<img src="/images/checbox.svg" style={{width: "28px"}}
                                                                     alt=""/>}/>
                    <label className="checkbox-label" style={{
                      fontSize: "14px",
                    }}>Запомнить меня</label>
                  </div>
                </div>
              </div>
              <button type="submit" onClick={login} className="btn btn-primary"><p>Войти</p></button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}


export default LoginForm;
