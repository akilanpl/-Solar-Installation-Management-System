"use client";
import {Workspace} from "@/components/workspace";
import {PaymentAvailability} from "@/components/payment-availability";
export default function Page(){return <Workspace path="/customer/payments/razorpay">{()=> <PaymentAvailability/>}</Workspace>;}
