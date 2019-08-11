package com.example.myapplication;

import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Headers;
import retrofit2.http.Multipart;
import retrofit2.http.POST;
import retrofit2.http.Part;
import retrofit2.http.Url;

public interface UploadAPIs {
    @Multipart
    @POST("/receive")
    Call<ResponseBody> uploadImage(@Part("name") RequestBody name, @Part MultipartBody.Part image);

    @GET("/download")
    Call<ResponseBody> downloadFile();
}
