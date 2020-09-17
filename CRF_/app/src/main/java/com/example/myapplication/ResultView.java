package com.example.myapplication;

import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import android.app.ProgressDialog;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.DialogInterface;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.nfc.Tag;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.view.View;
import android.widget.ImageView;
import android.widget.Toast;

import com.afollestad.materialdialogs.MaterialDialog;
import com.squareup.picasso.MemoryPolicy;
import com.squareup.picasso.NetworkPolicy;
import com.squareup.picasso.Picasso;
import com.squareup.picasso.Target;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;


public class ResultView extends AppCompatActivity {

    private String currentImageURL = "";
    private ImageView result_iv;
    private Bitmap ResultImage = null;
    private String imageDir = "imageDir";
    private String imageName = "my_image.jpg";
    private static ProgressDialog progressDialog;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_result_view);
        progressDialog = new ProgressDialog(this);

        result_iv = (ImageView)findViewById(R.id.resultview);
        //저장 버튼 이벤트
        findViewById(R.id.btn_save).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                show();
            }
        });
        // 사진 처리 후 imageview에 띄우기
        showImage();
    }

    // 사진 처리 후 imageview에 띄우기
    private void showImage(){
        // imageview에 이미지 가져오기
        Bitmap bit = ((BitmapDrawable)ContentView.iv.getDrawable()).getBitmap();
        // 객체를 흰색으로 바꿈
        bit = changeColorToWhite(bit, ContentView.option_switch.isChecked());
        // imageview에 이미지 가져오기

        File storage = getApplication().getCacheDir();
        String fileName = "IMG_" + System.currentTimeMillis() + ".jpg";
        File temp = new File(storage, fileName);


        try{
            temp.createNewFile();
            FileOutputStream out = new FileOutputStream(temp);
            bit.compress(Bitmap.CompressFormat.JPEG, 90, out);
            out.close();
        }catch(FileNotFoundException e){
            e.printStackTrace();
        }catch (IOException e){
            e.printStackTrace();
        }

        //이미지 업로드
        passToServer(temp.getAbsolutePath());

        //Bitmap bitMask = ((BitmapDrawable)ContentView.iv.getDrawable()).getBitmap();
        // Mask 이미지를 만듬
        Bitmap bitMask = changeColorToMask(bit, ContentView.option_switch.isChecked());
        //bitmap 이미지를 임시 파일로 저장

        fileName = "IMG_" + System.currentTimeMillis() + ".jpg";
        File tempMask = new File(storage, fileName);

        try{
            tempMask.createNewFile();
            FileOutputStream out = new FileOutputStream(tempMask);
            bitMask.compress(Bitmap.CompressFormat.JPEG, 90, out);
            out.close();
        }catch(FileNotFoundException e){
            e.printStackTrace();
        }catch (IOException e){
            e.printStackTrace();
        }

        //Mask 업로드
        passMaskToServer(tempMask.getAbsolutePath());
        //처리된 이미지 다운로드
        downloadToServer();
    }

    private Bitmap changeColorToWhite(Bitmap src, boolean check) {
        int width = src.getWidth();
        int height = src.getHeight();
        int[] pixels = new int[width * height];

        float upX, downX, upY, downY;

        // 픽셀정보 받아오기
        src.getPixels(pixels, 0, width, 0, 0, width, height);
        // 새로운 bitmap 만들기
        Bitmap bmOut = Bitmap.createBitmap(width, height, src.getConfig());

        // 일괄 삭제 시 선택한 객체 원상복구
        if(check){
            for(int i = 0 ; i < ContentView.CheckArr.size(); i++){
                if(ContentView.CheckArr.get(i)){
                    upX = ContentView.LocationArr.get(i).getfloatXup();
                    downX = ContentView.LocationArr.get(i).getfloatXdown();
                    upY =ContentView.LocationArr.get(i).getfloatYup();
                    downY = ContentView.LocationArr.get(i).getfloatYdown();

                    for (int y = (int)downY; y < (int)upY; ++y) {
                        for (int x = (int)downX; x < (int)upX; ++x) {
                            int index = y * width + x;
                            pixels[index] = ContentView.OriginPixels[index];
                        }
                    }
                }
            }
        }

        // 해당 객체들을 흰색으로 처리함
        for(int t = 0 ; t < ContentView.CheckArr.size(); t++){
            if((ContentView.CheckArr.get(t) && (!check)) || (!ContentView.CheckArr.get(t) && check)){
                upX = ContentView.LocationArr.get(t).getfloatXup();
                downX = ContentView.LocationArr.get(t).getfloatXdown();
                upY =ContentView.LocationArr.get(t).getfloatYup();
                downY = ContentView.LocationArr.get(t).getfloatYdown();

                for (int y = (int)downY; y < (int)upY; y++) {
                    for (int x = (int)downX; x < (int)upX; x++) {
                        int index = y * width + x;
                        pixels[index] = Color.argb(255, 255, 255, 255);
                    }
                }
            }
        }
        //바뀐 픽셀 저장
        bmOut.setPixels(pixels, 0, width, 0, 0, width, height);
        return bmOut;
    }

    private Bitmap changeColorToMask(Bitmap src, boolean check) {
        int width = src.getWidth();
        int height = src.getHeight();
        int[] pixels = new int[width * height];

        float upX, downX, upY, downY;

        // 픽셀정보 받아오기
        src.getPixels(pixels, 0, width, 0, 0, width, height);
        // 새로운 bitmap 만들기
        Bitmap bmOut = Bitmap.createBitmap(width, height, src.getConfig());


        // 객체 이외의 배경을 검은색으로
        for(int y = 0; y < height; y++){
            for(int x = 0 ; x < width; x++){
                boolean CHECK = true;
                for(int t = 0 ; t < ContentView.CheckArr.size(); t++){
                    if((ContentView.CheckArr.get(t) && (!check)) || (!ContentView.CheckArr.get(t) && check)) {
                        upX = ContentView.LocationArr.get(t).getfloatXup();
                        downX = ContentView.LocationArr.get(t).getfloatXdown();
                        upY = ContentView.LocationArr.get(t).getfloatYup();
                        downY = ContentView.LocationArr.get(t).getfloatYdown();
                        if (x >= downX && x < upX && y >= downY && y < upY){
                            CHECK = false;
                            break;
                        }
                    }
                }
                if(CHECK){
                    int index = y * width + x;
                    pixels[index] = Color.argb(255, 0, 0, 0);
                }
            }
        }

        //바뀐 픽셀 저장
        bmOut.setPixels(pixels, 0, width, 0, 0, width, height);
        return bmOut;
    }

    public static void passToServer(String filePath) {
        File file = new File(filePath);
        RequestBody mFile = RequestBody.create(MediaType.parse("image/*"), file);
        MultipartBody.Part fileToUpload = MultipartBody.Part.createFormData("file", file.getName(), mFile);
        RequestBody filename = RequestBody.create(MediaType.parse("text/plain"), file.getName());
        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(NetworkClient.BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build();
        UploadAPIs PassImage = retrofit.create(UploadAPIs.class);
        Call<ResponseBody> call = PassImage.passImage(filename, fileToUpload);

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {

            }
            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {

            }
        });
    }

    public static void passMaskToServer(String filePath) {
        File file = new File(filePath);
        RequestBody mFile = RequestBody.create(MediaType.parse("image/*"), file);
        MultipartBody.Part fileToUpload = MultipartBody.Part.createFormData("file", file.getName(), mFile);
        RequestBody filename = RequestBody.create(MediaType.parse("text/plain"), file.getName());
        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(NetworkClient.BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build();
        UploadAPIs PassImage = retrofit.create(UploadAPIs.class);
        Call<ResponseBody> call = PassImage.passImageMask(filename, fileToUpload);

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {

            }
            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {

            }
        });
    }

    void show(){
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("저장하기");
        builder.setMessage("사진이 잘 지워졌나요?");
        builder.setNegativeButton("아니오",
                new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        //Toast.makeText(getApplicationContext(),"아니오.",Toast.LENGTH_LONG).show();
                        Intent homeIntent = new Intent(getApplicationContext(), MainActivity.class);
                        homeIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                        homeIntent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
                        startActivity(homeIntent);
                        finish();
                    }
                });
        builder.setPositiveButton("예",
                new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        Bitmap bit = ((BitmapDrawable)result_iv.getDrawable()).getBitmap();
                        String fileName = "IMG_" + System.currentTimeMillis() + ".jpg";
                        File temp = new File(Environment.getExternalStorageDirectory().getAbsolutePath() + "/DCIM/Camera/", fileName);

                        try{
                            temp.createNewFile();
                            FileOutputStream out = new FileOutputStream(temp);
                            bit.compress(Bitmap.CompressFormat.JPEG, 90, out);
                            out.close();
                        }catch(FileNotFoundException e){
                            e.printStackTrace();
                        }catch (IOException e){
                            e.printStackTrace();
                        }
                        // 사진 리로딩
                        sendBroadcast(new Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE, Uri.fromFile(temp)));

                        insertDB();

                        Toast.makeText(getApplicationContext(),"저장되었습니다.",Toast.LENGTH_LONG).show();
                        Intent homeIntent = new Intent(getApplicationContext(), MainActivity.class);
                        homeIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                        homeIntent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
                        startActivity(homeIntent);
                        finish();
                    }
                });
        builder.show();
    }

    private void downloadToServer() {
        /*Picasso.with(getApplicationContext())
                .load(NetworkClient.BASE_URL + "/download")
                .placeholder(R.drawable.progress_animation)
                .into(result_iv);*/

        OkHttpClient okHttpClient = new OkHttpClient.Builder()
                .connectTimeout(1, TimeUnit.MINUTES)
                .readTimeout(60, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .build();

        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(NetworkClient.BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build();
        UploadAPIs uploadImage = retrofit.create(UploadAPIs.class);
        Call<ResponseBody> call = uploadImage.downloadImage();

        progressDialog.setProgressStyle(ProgressDialog.STYLE_SPINNER);
        progressDialog.setIndeterminate(true);
        progressDialog.setMessage("Loading...");
        progressDialog.show();


        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
                if(response.isSuccessful()){
                    boolean writtenToDisk = writeResponseBodyToDisk(response.body());
                }
                progressDialog.dismiss();
            }

            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
                progressDialog.dismiss();
            }
        });

    }

    private boolean writeResponseBodyToDisk(ResponseBody body) {
        try {
            // todo change the file location/name according to your needs
            File temp = new File(getExternalFilesDir(null) + File.separator + "temp.jpg");
            Log.d("TAG", "ExternalFilesDir(ROOT) : " + this.getExternalFilesDir(null));

            InputStream inputStream = null;
            OutputStream outputStream = null;

            try {
                byte[] fileReader = new byte[4096];

                long fileSize = body.contentLength();
                long fileSizeDownloaded = 0;

                inputStream = body.byteStream();
                outputStream = new FileOutputStream(temp);

                while (true) {
                    int read = inputStream.read(fileReader);
                    if (read == -1) {
                        break;
                    }

                    outputStream.write(fileReader, 0, read);

                    fileSizeDownloaded += read;
                }

                outputStream.flush();

                return true;
            } catch (IOException e) {
                return false;
            } finally {
                if (inputStream != null) {
                    inputStream.close();
                }

                if (outputStream != null) {
                    outputStream.close();
                }
                Bitmap bitmap = BitmapFactory.decodeFile(temp.getAbsolutePath());

                result_iv.setImageBitmap(bitmap);
            }
            //Bitmap bitmap = BitmapFactory.decodeFile(temp.getAbsolutePath());
            //result_iv.setImageBitmap(bitmap);
        } catch (IOException e) {
            return false;
        }
    }

    private void insertDB(){
        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(NetworkClient.BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build();
        UploadAPIs insertDB = retrofit.create(UploadAPIs.class);
        Call<ResponseBody> call = insertDB.insertDB();

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
            }
            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
            }
        });
    }
}
