import csv

def generate_csv(report):

    file_path = "user_report.csv"

    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)

        writer.writerow(["Metric", "Value"])

        for key, value in report.items():
            writer.writerow([key, value])

    return file_path