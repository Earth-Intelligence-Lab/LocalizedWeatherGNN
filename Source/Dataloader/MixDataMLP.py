# Author: Qidong Yang & Jonathan Giezendanner

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from Source.Dataloader.MixData import MixData


class MixDataMLP(MixData):
    def __init__(self, year, back_hrs, lead_hours, meta_station, madis_network, n_neighbors_m2m,
                 era5_network, root_path=Path('')):
        MixData.__init__(self, year, back_hrs, lead_hours, meta_station, madis_network, n_neighbors_m2m, era5_network,
                         root_path)

        if self.era5_network is not None:

            interpolated_file_path = root_path / 'ERA5' / 'Interpolated' / f'era5interpolated_e2m_{era5_network.n_neighbors_e2m}_{year}_{meta_station.filtered_file_name}.nc'
            if interpolated_file_path.exists():
                self.era5_data = xr.open_dataset(interpolated_file_path)
                return

            data = self.era5_data
            u10 = np.moveaxis(data.u10.values, 0, -1).reshape((era5_network.era5_pos.size(0), -1))
            u10_sub = u10[era5_network.e2m_edge_index[0, :]]
            v10 = np.moveaxis(data.v10.values, 0, -1).reshape((era5_network.era5_pos.size(0), -1))
            v10_sub = v10[era5_network.e2m_edge_index[0, :]]
            t2m = np.moveaxis(data.t2m.values, 0, -1).reshape((era5_network.era5_pos.size(0), -1))
            t2m_sub = t2m[era5_network.e2m_edge_index[0, :]]
            d2m = np.moveaxis(data.d2m.values, 0, -1).reshape((era5_network.era5_pos.size(0), -1))
            d2m_sub = d2m[era5_network.e2m_edge_index[0, :]]
            ssr = np.moveaxis(data.ssr.values, 0, -1).reshape((era5_network.era5_pos.size(0), -1))
            ssr_sub = ssr[era5_network.e2m_edge_index[0, :]]

            rel_distances_era5 = era5_network.e2m_relativeDistance.cpu().numpy()

            df = pd.DataFrame(columns=['u', 'v', 'temp', 'dewpoint', 'solar_radiation'])

            for k in range(u10_sub.shape[0]):
                df.loc[k, 'u'] = u10_sub[k, :] * rel_distances_era5[k].squeeze()
                df.loc[k, 'v'] = v10_sub[k, :] * rel_distances_era5[k].squeeze()
                df.loc[k, 'temp'] = t2m_sub[k, :] * rel_distances_era5[k].squeeze()
                df.loc[k, 'dewpoint'] = d2m_sub[k, :] * rel_distances_era5[k].squeeze()
                df.loc[k, 'solar_radiation'] = ssr_sub[k, :] * rel_distances_era5[k].squeeze()

            df['madis_index'] = era5_network.e2m_edge_index[1, :]

            sumdf = df.groupby('madis_index').sum()

            u = np.stack(sumdf.u.values)
            v = np.stack(sumdf.v.values)
            temp = np.stack(sumdf.temp.values)
            dewpoint = np.stack(sumdf.dewpoint.values)
            solar_radiation = np.stack(sumdf.solar_radiation.values)

            data = self.madis_data.copy()
            data = data.drop(
                ['u_is_real', 'v_is_real', 'temp_is_real', 'dewpoint_is_real', 'solar_radiation_is_real', 'elv'])
            data.u.values = u
            data.v.values = v
            data.temp.values = temp
            data.dewpoint.values = dewpoint
            data.solar_radiation.values = solar_radiation

            data = data.rename(dict(
                {'u': 'u10', 'v': 'v10', 'temp': 't2m', 'dewpoint': 'd2m', 'solar_radiation': 'ssr', 'lon': 'era5_lons',
                 'lat': 'era5_lats'}))

            interpolated_file_path.parent.mkdir(exist_ok=True, parents=True)
            data.to_netcdf(interpolated_file_path)

            self.era5_data = data
