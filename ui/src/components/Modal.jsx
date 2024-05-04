import React from 'react';
import "../styles/modal.css"

const Modal = ({ isOpen, children }) => {
  if (!isOpen) return null;

  return (
    <div className="modal">
      {children}
    </div>
  );
};

export default Modal;
