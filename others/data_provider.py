from abc import ABC, abstractmethod

import pandas as pd


class DataProvider(ABC):
    """Abstract class that defines a data provider from a target"""

    @abstractmethod
    def get_market_list(self) -> list:
        raise NotImplementedError()

    @abstractmethod
    def get_market_forecast_date_range(self, market: str) -> list:
        raise NotImplementedError()

    @abstractmethod
    def get_market_forecast_data(self, market: str, start_date: str, end_date: str):
        raise NotImplementedError()


class DebugDataProvider(DataProvider):
    """Data Provider for debug purposes"""

    PATH = "/Users/jorge/Documents/alto"

    def get_market_list(self) -> list:
        return sorted(["dallas", "houston", "LA", "miami", "SV", "washington"])

    def get_market_forecast_date_range(self, market: str) -> list:
        df = pd.read_csv(
            f"{self.PATH}/actuals_forecasts_{market}.csv",
            usecols=["for_date"],
            parse_dates=[0],
        )
        return df["for_date"].min(), df["for_date"].max()

    def get_market_forecast_data(self, market: str, start_date: str, end_date: str):
        df = pd.read_csv(
            f"{self.PATH}/actuals_forecasts_{market}.csv",
        )

        # Filter date
        df = df[df["for_date"].between(start_date, end_date)]

        # Join date with hours
        df["time"] = pd.to_datetime(
            df["for_date"] + " " + df["for_hour"].astype(str).str.zfill(2),
            format="%Y-%m-%d %H",
            utc=True,
        )
        df = df.set_index("time").drop(columns=["for_date", "for_hour"])
        df.columns = ["forecast", "real"]
        return df
