"use client";
import { WeatherOps } from "@/components/weather";
import { Workspace } from "@/components/workspace";
export default function Page() { return <Workspace path="/support/weather">{() => <WeatherOps />}</Workspace>; }
