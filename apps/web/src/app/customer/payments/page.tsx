"use client";
import {Workspace} from "@/components/workspace";
import {Quotations} from "@/components/quotations";
import {ReceiptPrinter} from "@/components/receipt-printer";
export default function Page(){return <Workspace path="/customer/payments">{()=> <><Quotations showPayments/><ReceiptPrinter/></>}</Workspace>;}
