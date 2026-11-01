import React from 'react';
import { TransactionCard } from '../TransactionCard/TransactionCard';
import '../TransactionCard/TransactionCard.css';

/**
 * PosTransactionCard - Alias component for animated POS Terminal card
 */
export function PosTransactionCard(props) {
  return <TransactionCard {...props} />;
}

export default PosTransactionCard;
