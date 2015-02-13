import pandas as pd

from flask import Flask
app = Flask(__name__)


@app.route("/")
def servetable():
    df = pd.DataFrame.from_csv('bible-genealogy.csv')
    return df.to_html()

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)  # TODO: debug production setting?
