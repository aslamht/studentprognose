import pandas as pd
import numpy as np
import os
import sys
import datetime

arguments = sys.argv
years = []
year_slice = False

for i in range(1, len(arguments)):
    arg = arguments[i]
    if arg == "-y" or arg == "-year":
        continue
    elif arg == ":":
        year_slice = True
    elif arg.isnumeric():
        if year_slice:
            last_year = years.pop(-1)
            years = years + list(range(last_year, int(arg) + 1))
            year_slice = False
        else:
            years.append(int(arg))

if years == []:
    current_year = datetime.date.today().year

data = pd.read_excel(
    "//ru.nl/wrkgrp/TeamIR/Man_info/Student Analytics/Prognosemodel RU/Syntax/Python/studentprognose/data/input/totaal.xlsx"
)

data = data.replace(np.inf, np.nan)

data = data.rename(
    columns={
        "MAE weighted ensemble": "MAE_Weighted_ensemble_prediction",
        "MAE average ensemble": "MAE_Average_ensemble_prediction",
        "MAE ensemble": "MAE_Ensemble_prediction",
        "MAE ratio": "MAE_Prognose_ratio",
        "MAE sarima cumulative": "MAE_SARIMA_cumulative",
        "MAE sarima individual": "MAE_SARIMA_individual",
        "MAPE weighted ensemble": "MAPE_Weighted_ensemble_prediction",
        "MAPE average ensemble": "MAPE_Average_ensemble_prediction",
        "MAPE ensemble": "MAPE_Ensemble_prediction",
        "MAPE ratio": "MAPE_Prognose_ratio",
        "MAPE sarima cumulative": "MAPE_SARIMA_cumulative",
        "MAPE sarima individual": "MAPE_SARIMA_individual",
    }
)

percentage_range = range(10, 150, 10)

methods = ["SARIMA_cumulative", "SARIMA_individual", "Prognose_ratio"]


def calculate_weight_distribution(metrics, percentage, second_percentage):
    # print(f"Metrics {metrics}")
    sorted(metrics, key=lambda x: x[1])
    # print(f"Metrics {metrics}")
    result = [(m[0], 0.0) for m in metrics]

    first_threshold = 1.0 + (float(percentage) / 100)
    second_threshold = 1.0 + (float(second_percentage) / 100)

    # Check if first method is best
    if metrics[1][1] > metrics[0][1] * first_threshold:
        result[0] = (result[0][0], 1.0)
        return result

    # Check if second method is still better than third
    elif metrics[2][1] > metrics[1][1] * second_threshold:
        m1 = metrics[0][1]
        m2 = metrics[1][1]
        total = m1 + m2
        new_total = total / m1 + total / m2

        result[0] = (result[0][0], (total / m1) / new_total)
        result[1] = (result[1][0], (total / m2) / new_total)
        return result

    # Combine all
    else:
        total = sum([m[1] for m in metrics])
        new_total = sum([total / m[1] for m in metrics])
        result = [(m[0], (total / m[1]) / new_total) for m in metrics]
        return result


def get_metric_weight_distribution(
    data, programme, examentype, herkomst, percentage, second_percentage, methods
):
    # print(programme, herkomst)
    data = data[
        (data["Croho groepeernaam"] == programme)
        & (data["Examentype"] == examentype)
        & (data["Herkomst"] == herkomst)
    ]

    MAE = [(method, np.nanmean(data[f"MAE_{method}"])) for method in methods]
    MAE = calculate_weight_distribution(MAE, percentage, second_percentage)
    # print(f"MAE: {MAE}")

    MAPE = [(method, np.nanmean(data[f"MAPE_{method}"]) / len(data) * 100) for method in methods]
    MAPE = calculate_weight_distribution(MAPE, percentage, second_percentage)
    # print(f"MAPE: {MAPE}")

    return MAE, MAPE


weight_distribution = {
    "Collegejaar": [],
    "Programme": [],
    "Herkomst": [],
    "Percentage": [],
    "Second percentage": [],
}

MAEs = []
MAPEs = []

print("Calculating weight distribution...")
for year in years:
    print(f"Year: {year}")
    data_temp = data[data["Collegejaar"] < year]
    for percentage in percentage_range:
        print(f"Percentage: {percentage}")
        for second_percentage in percentage_range:
            for programme in data_temp["Croho groepeernaam"].unique():
                for examentype in data_temp[data_temp["Croho groepeernaam"] == programme][
                    "Examentype"
                ].unique():
                    for herkomst in data_temp["Herkomst"].unique():
                        weight_distribution["Collegejaar"].append(year)
                        weight_distribution["Programme"].append(programme)
                        weight_distribution["Examentype"].append(examentype)
                        weight_distribution["Herkomst"].append(herkomst)
                        weight_distribution["Percentage"].append(percentage)
                        weight_distribution["Second percentage"].append(second_percentage)

                        MAE, MAPE = get_metric_weight_distribution(
                            data_temp,
                            programme,
                            examentype,
                            herkomst,
                            percentage,
                            second_percentage,
                            methods,
                        )

                        MAEs.append(MAE)
                        MAPEs.append(MAPE)

for m in methods:
    weight_distribution[f"MAE_{m}"] = [dict(MAE)[m] for MAE in MAEs]
    weight_distribution[f"MAPE_{m}"] = [dict(MAPE)[m] for MAPE in MAPEs]

weight_data = pd.DataFrame(weight_distribution)

if os.path.isfile("configuration/weight_distribution.xlsx"):
    existing_weight_data = pd.read_excel("configuration/weight_distribution.xlsx")
    existing_weight_data = existing_weight_data[~existing_weight_data["Collegejaar"].isin(years)]
    weight_data = pd.concat([existing_weight_data, weight_data])
    weight_data = weight_data.sort_values(
        by=["Collegejaar", "Programme", "Herkomst", "Percentage", "Second percentage"]
    )

weight_data.to_excel("configuration/weight_distribution.xlsx", index=False)


def mean_absolute_error(true, prediction):
    return abs(true - prediction)


def mean_absolute_percentage_error(true, prediction):
    return abs((true - prediction) / true)


print("Calculating error rates...")
error_rates = {
    "Collegejaar": [],
    "Percentage": [],
    "Second percentage": [],
    "MAE": [],
    "MAPE": [],
    "Herkomst": [],
    "MAE of AE": [],
    "MAPE of AE": [],
}
for year in years:
    print(f"Year: {year}")
    temp_filtered_weight_data_year = weight_data[weight_data["Collegejaar"] == year]
    for herkomst in ["EER", "NL", "Niet-EER"]:
        temp_filtered_weight_data_herkomst = temp_filtered_weight_data_year[
            temp_filtered_weight_data_year["Herkomst"] == herkomst
        ]
        print(f"Herkomst: {herkomst}")
        for percentage in percentage_range:
            temp_filtered_weight_data_percentage = temp_filtered_weight_data_herkomst[
                temp_filtered_weight_data_herkomst["Percentage"] == percentage
            ]
            for second_percentage in percentage_range:
                filtered_weight_data = temp_filtered_weight_data_percentage[
                    temp_filtered_weight_data_percentage["Second percentage"] == second_percentage
                ]

                error_rates["Collegejaar"].append(year)
                error_rates["Percentage"].append(percentage)
                error_rates["Second percentage"].append(second_percentage)

                MAE_total = 0.0
                MAPE_total = 0.0

                MAE_total_AE = 0.0
                MAPE_total_AE = 0.0

                for i, row_weight in filtered_weight_data.iterrows():
                    filtered_data = data[
                        (data["Croho groepeernaam"] == row_weight["Programme"])
                        & (data["Examentype"] == row_weight["Examentype"])
                        & (data["Collegejaar"] < row_weight["Collegejaar"])
                        & (data["Collegejaar"] >= 2021)
                        & (data["Herkomst"] == row_weight["Herkomst"])
                    ]

                    use_average_ensemble = False
                    if sum([row_weight[f"MAE_{method}"] for method in methods]) != 1:
                        use_average_ensemble = True

                    MAE_subtotal = 0.0
                    MAPE_subtotal = 0.0

                    MAE_subtotal_AE = 0.0
                    MAPE_subtotal_AE = 0.0
                    for j, row in filtered_data.iterrows():
                        if use_average_ensemble:
                            if not np.isnan(row["MAE_Average_ensemble_prediction"]):
                                MAE_subtotal += row["MAE_Average_ensemble_prediction"]
                            if not np.isnan(row["MAPE_Average_ensemble_prediction"]):
                                MAPE_total += row["MAPE_Average_ensemble_prediction"]
                        else:
                            if all(
                                [(not np.isnan(row[method])) for method in methods]
                            ) and not np.isnan(row["Aantal_studenten"]):
                                new_ensemble_prediction = sum(
                                    [
                                        (row[method] * row_weight[f"MAE_{method}"])
                                        for method in methods
                                    ]
                                )
                                MAE_subtotal += mean_absolute_error(
                                    row["Aantal_studenten"], new_ensemble_prediction
                                )
                                MAPE_subtotal += mean_absolute_percentage_error(
                                    row["Aantal_studenten"], new_ensemble_prediction
                                )

                        if not np.isnan(row["MAE_Average_ensemble_prediction"]):
                            MAE_subtotal_AE += row["MAE_Average_ensemble_prediction"]
                        if not np.isnan(row["MAPE_Average_ensemble_prediction"]):
                            MAPE_subtotal_AE += row["MAPE_Average_ensemble_prediction"]

                    count = len(filtered_data)
                    if count == 0:
                        count = 1

                    MAE_total += MAE_subtotal / count
                    MAPE_total += MAPE_subtotal / count * 100

                    # print(MAE_total)

                    MAE_total_AE += MAE_subtotal_AE / count
                    MAPE_total_AE += MAPE_subtotal_AE / count * 100

                error_rates["MAE"].append(MAE_total / len(filtered_weight_data))
                error_rates["MAPE"].append(MAPE_total / len(filtered_weight_data))
                error_rates["Herkomst"].append(herkomst)
                error_rates["MAE of AE"].append(MAE_total_AE / len(filtered_weight_data))
                error_rates["MAPE of AE"].append(MAPE_total_AE / len(filtered_weight_data))

error_rates = pd.DataFrame(error_rates)

if os.path.isfile("configuration/error_rates.xlsx"):
    existing_error_rates = pd.read_excel("configuration/error_rates.xlsx")
    existing_error_rates = existing_error_rates[~existing_error_rates["Collegejaar"].isin(years)]
    error_rates = pd.concat([existing_error_rates, error_rates])
    error_rates = error_rates.sort_values(by=["Collegejaar", "Percentage", "Second percentage"])

error_rates.to_excel("configuration/error_rates.xlsx", index=False)

# error_rates = pd.read_excel("configuration/error_rates.xlsx")
# weight_data = pd.read_excel("configuration/weight_distribution.xlsx")

print("Calculating ensemble weights...")
ensemble_weights = {
    "Collegejaar": [],
    "Programme": [],
    "Examentype": [],
    "Herkomst": [],
    "SARIMA_cumulative": [],
    "SARIMA_individual": [],
    "Prognose_ratio": [],
    "Average_ensemble_prediction": [],
}
for year in years:
    year_temp_data = error_rates[error_rates["Collegejaar"] == year]
    percentage_per_herkomst = {"EER": (), "NL": (), "Niet-EER": ()}
    for herkomst in percentage_per_herkomst.keys():
        temp_data = year_temp_data[year_temp_data["Herkomst"] == herkomst]
        temp_data = temp_data[temp_data["MAE"] == temp_data["MAE"].min()]
        percentage_per_herkomst[herkomst] = (
            float(temp_data["Percentage"].iloc[0]),
            float(temp_data["Second percentage"].iloc[0]),
        )

        temp_data = weight_data[
            (weight_data["Herkomst"] == herkomst) & (weight_data["Collegejaar"] == year)
        ]
        temp_data = temp_data[temp_data["Percentage"] == percentage_per_herkomst[herkomst][0]]
        temp_data = temp_data[
            temp_data["Second percentage"] == percentage_per_herkomst[herkomst][1]
        ]

        for i, row in temp_data.iterrows():
            ensemble_weights["Collegejaar"].append(year)
            ensemble_weights["Programme"].append(row["Programme"])
            ensemble_weights["Examentype"].append(row["Examentype"])
            ensemble_weights["Herkomst"].append(row["Herkomst"])

            average_ensemble_weight = 0.0

            MAEs = [row[f"MAE_{method}"] for method in methods]
            sum_MAE = sum(MAEs)

            if sum_MAE != 1 or sum_MAE == 0:
                average_ensemble_weight = 1.0
                MAEs = [0.0] * len(methods)

            for m in range(len(methods)):
                ensemble_weights[methods[m]].append(MAEs[m])

            ensemble_weights["Average_ensemble_prediction"].append(average_ensemble_weight)

ensemble_weights = pd.DataFrame(ensemble_weights)

if os.path.isfile("configuration/ensemble_weights.xlsx"):
    existing_ensemble_weights = pd.read_excel("configuration/ensemble_weights.xlsx")
    existing_ensemble_weights = existing_ensemble_weights[
        ~existing_ensemble_weights["Collegejaar"].isin(years)
    ]
    ensemble_weights = pd.concat([existing_ensemble_weights, ensemble_weights])
    ensemble_weights = ensemble_weights.sort_values(
        by=["Collegejaar", "Programme", "Examentype", "Herkomst"]
    )

ensemble_weights.to_excel("configuration/ensemble_weights.xlsx", index=False)
