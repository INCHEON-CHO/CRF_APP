package com.example.myapplication;

import android.content.Context;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import okhttp3.OkHttpClient;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class NetworkClient {
    public static final String BASE_URL = "http://115.23.130.56";
            private static Retrofit retrofit;
            public static Retrofit getRetrofitClient(Context context) {
                if (retrofit == null) {
                    OkHttpClient okHttpClient = new OkHttpClient.Builder()
                            .build();
                    Gson gson = new GsonBuilder()
                            .setLenient()
                            .create();
                    retrofit = new Retrofit.Builder()
                            .baseUrl(BASE_URL)
                            .client(okHttpClient)
                            .addConverterFactory(GsonConverterFactory.create(gson))
                            .build();
        }
        return retrofit;
    }
}
