package com.example.myapplication;

import com.google.gson.annotations.SerializedName;

public class UploadObject {
    private  String success;
    public UploadObject(String success){
        this.success = success;
    }
    public String getSuccess(){
        return this.success;
    }
}
