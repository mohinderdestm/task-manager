import csv

def generate_csv(report: dict, user_id: str = "unknown") -> str:

    file_path = f"report_{user_id}.csv"

    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Metric", "Value"])

        for key, value in report.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    writer.writerow([f"{key}.{sub_key}", sub_value])
            elif isinstance(value, list):
                writer.writerow([key, str(value)])
            else:
                writer.writerow([key, value])

    return file_path