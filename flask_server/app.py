from flask import Flask, request, jsonify, send_file
from werkzeug import secure_filename
import json, io, skimage.io, os
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
        Filename = secure_filename(file.filename)
        file.save(Filename)
        #path = os.path.dirname(os.path.realpath(__file__)) + "\\" + Filename
        #path = os.path.dirname(os.path.realpath(__file__)) + "\\images.jpg"
        #result = skimage.io.imread(path)
        #location = (result[0])['rois']  
        """
            객체 좌표 전달
        """
        return jsonify({'you send this': 'error'})
    else:
        return "Y U NO USE POST?"

@app.route('/download')
def downloadFile():
    return send_file('C:\\Users\\gther\\OneDrive\\Desktop\\CRF_APP\\flask_server\\IMG_083453.jpg')

    

# running web app in local machine
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)