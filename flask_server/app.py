from flask import Flask, request, jsonify, send_file
from werkzeug import secure_filename
import json, io
app = Flask(__name__)


# root
@app.route("/")
def index():
    """
    this is a root dir of my server
    :return: str
    """
    return "This is root"

    

@app.route('/receive',methods=['POST', 'GET'])
def getFile():
    if request.method == 'POST':
        file = request.files['file']
        print("get files")
        file.save(secure_filename(file.filename))
        """
            객체 좌표 전달
        """
        return jsonify({'you send this': 'error'})
    else:
        return "Y U NO USE POST?"

@app.route('/download')
def downloadFile():
    return send_file('C:\\Users\\gther\\Desktop\\flask\\IMG_044911.jpg', attachment_filename="image.jpg")

    

# running web app in local machine
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)