package com.example.myapplication;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;

import android.app.Activity;
import android.app.ProgressDialog;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.drawable.BitmapDrawable;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.widget.CompoundButton;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.Switch;
import android.widget.Toast;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.io.DataOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.ByteBuffer;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.WeakHashMap;
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

public class ContentView extends AppCompatActivity{

    public static List<Location> LocationArr = new ArrayList<Location>();
    public static List<Boolean> CheckArr = new ArrayList<Boolean>();
    public static final String TAG = MainActivity.class.getSimpleName();
    private  File tempFile;
    private  String currentPhotoPath;
    private static ProgressDialog progressDialog;
    private static final int PICK_FROM_CAMERA = 1;
    private static final int PICK_FROM_ALBUM = 2;
    private  Bitmap bitmap;
    public static ImageView iv;
    public static Switch option_switch;
    private final int GAP = 10;
    public static final int WEIGHT = 5;
    public static int[] OriginPixels;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_content_view);

         iv = (ImageView)findViewById(R.id.contentview);
         option_switch = (Switch)(findViewById(R.id.switch1));
         progressDialog = new ProgressDialog(this);

        Intent intent = getIntent();
        int num = intent.getExtras().getInt("num");

        switch(num){
            case PICK_FROM_CAMERA:
                takePhoto();
                break;
            case PICK_FROM_ALBUM:
                goToAlbum();
                break;
            default:
        }

        // 객체를 터치했을 때 표시해줌
        findViewById(R.id.contentview).setOnTouchListener(new View.OnTouchListener() {
            float floatx, floaty;
                @Override
                public boolean onTouch(View view, MotionEvent motionEvent) {
                    if(motionEvent.getAction() == MotionEvent.ACTION_UP){
                        floatx = motionEvent.getX();
                        floaty = motionEvent.getY();
                        //Toast.makeText(getApplicationContext(), floatx + " " + floaty, Toast.LENGTH_SHORT).show();

                        for(int i = 0 ; i < LocationArr.size(); i++){
                            if((LocationArr.get(i).getfloatXup() + GAP >= floatx && LocationArr.get(i).getfloatXdown() - GAP <= floatx) &&
                                (LocationArr.get(i).getfloatYup() + GAP >= floaty && LocationArr.get(i).getfloatYdown() - GAP <= floaty)){
                                Bitmap bit = ((BitmapDrawable)iv.getDrawable()).getBitmap();
                                Bitmap ModifiedBitmap = changeColor(bit, LocationArr.get(i).getfloatXup(), LocationArr.get(i).getfloatXdown(),
                                        LocationArr.get(i).getfloatYup(), LocationArr.get(i).getfloatYdown(), CheckArr.get(i));
                                CheckArr.set(i, !CheckArr.get(i));
                                iv.setImageBitmap(ModifiedBitmap);
                    }
                }
        }
        return true;
            }
        });
        // 다음 화면으로 전환
        findViewById(R.id.btn_apply).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                //화면 전환
                Intent intent = new Intent(getApplicationContext(), ResultView.class);
                startActivity(intent);
            }
        });

        option_switch.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton compoundButton, boolean b) {
                if(!b){ // 선택 삭제일 때
                    option_switch.setText("선택 삭제");
                    Toast.makeText(getApplicationContext(), "삭제할 객체를 선택하세요", Toast.LENGTH_SHORT).show();
                }
                else{ //일괄 삭제일 때
                    option_switch.setText("일괄 삭제");
                    Toast.makeText(getApplicationContext(), "남겨질 객체를 선택하세요", Toast.LENGTH_SHORT).show();
                }
            }
        });
    }

    private Bitmap changeColor(Bitmap src, float upX, float downX, float upY, float downY, boolean check) {
        int width = src.getWidth();
        int height = src.getHeight();
        int[] pixels = new int[width * height];
        // get pixel array from source
        src.getPixels(pixels, 0, width, 0, 0, width, height);
        Bitmap bmOut = Bitmap.createBitmap(width, height, src.getConfig());

        if(!check){
            for (int y = (int)downY; y < (int)upY; ++y) {
                for (int x = (int)downX; x < (int)upX; ++x) {
                    if(upX - WEIGHT <= x || downX + WEIGHT >= x || upY - WEIGHT <= y || downY + WEIGHT >= y){
                        // get current index in 2D-matrix
                        int index = y * width + x;
                        pixels[index] = Color.argb(255, 255, 0, 0);
                    }
                }
            }
        }
        else{
            for (int y = (int)downY; y < (int)upY; ++y) {
                for (int x = (int)downX; x < (int)upX; ++x) {
                    if(upX - WEIGHT <= x || downX + WEIGHT >= x || upY - WEIGHT <= y || downY + WEIGHT >= y){
                        // get current index in 2D-matrix
                        int index = y * width + x;
                        pixels[index] = OriginPixels[index];
                        //pixels[index] = Color.argb(255, 255, 0, 0);
                    }
                }
            }
        }
        bmOut.setPixels(pixels, 0, width, 0, 0, width, height);
        return bmOut;
    }

    private void takePhoto() {
        String state = Environment.getExternalStorageState();

        if(Environment.MEDIA_MOUNTED.equals(state)){
            Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);

            if(intent.resolveActivity(getPackageManager()) != null){
                try {
                    tempFile = createImageFile();

                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.N) {
                        Uri photoUri = FileProvider.getUriForFile(this, BuildConfig.APPLICATION_ID + ".fileprovider", tempFile);
                        //Uri photoUri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", tempFile);
                        intent.putExtra(MediaStore.EXTRA_OUTPUT, photoUri);
                        startActivityForResult(intent, PICK_FROM_CAMERA);
                    }
                    else {
                        Uri photoUri = Uri.fromFile(tempFile);
                        intent.putExtra(MediaStore.EXTRA_OUTPUT, photoUri);
                        startActivityForResult(intent, PICK_FROM_CAMERA);
                    }
                } catch (IOException e) {
                    Toast.makeText(this, "이미지 처리 오류! 다시 시도해주세요.", Toast.LENGTH_SHORT).show();
                    finish();
                    e.printStackTrace();
                }
            }
        }
    }

    private File createImageFile() throws IOException {

        // 이미지 파일 이름 ( blackJin_{시간}_ )
        String timeStamp = new SimpleDateFormat("HHmmss", java.util.Locale.getDefault()).format(new Date());
        String imageFileName = "IMG_" + timeStamp + ".jpg";

        // 빈 파일 생성
        File storageDir = new File(Environment.getExternalStorageDirectory().getAbsoluteFile() + "/DCIM/Camera/" + imageFileName);
        currentPhotoPath = storageDir.getAbsolutePath();

        return storageDir;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        if (resultCode != Activity.RESULT_OK) {

            Toast.makeText(this, "취소 되었습니다.", Toast.LENGTH_SHORT).show();
            if(tempFile != null) {
                if (tempFile.exists()) {
                    if (tempFile.delete()) {
                        Log.e(TAG, tempFile.getAbsolutePath() + " 삭제 성공");
                        tempFile = null;
                    }
                }
            }
            finish();
            return;
        }
        //카메라
        if(requestCode == PICK_FROM_CAMERA){
            //bitmap 가져오기
            bitmap = BitmapFactory.decodeFile(currentPhotoPath);
            //서버로 전송
            uploadToServer(currentPhotoPath);

            ExifInterface exif = null;
            try{
                exif = new ExifInterface(currentPhotoPath);
            }catch (IOException e){
                e.printStackTrace();
            }

            int exifOrientation;
            int exifDegree;

            if(exif != null){
                exifOrientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
                exifDegree = exifOrientationToDegress(exifOrientation);
            }
            else{
                exifDegree = 0;
            }
            this.sendBroadcast(new Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE, Uri.fromFile(tempFile)));

            //imageview에 표시
            iv.setImageBitmap(rotate(bitmap, exifDegree));
            //원본 bitmap 픽셀 저장
            Bitmap bit = ((BitmapDrawable)iv.getDrawable()).getBitmap();
            OriginPixels = new int[bit.getWidth() * bit.getHeight()];
            bit.getPixels(OriginPixels, 0, bit.getWidth(), 0, 0, bit.getWidth(), bit.getHeight());
        }
        //앨범
        else if (requestCode == PICK_FROM_ALBUM) {
            Uri photoUri = data.getData();
            Log.d(TAG, "PICK_FROM_ALBUM photoUri : " + photoUri);

            String imagePath = getRealPathFromURI(photoUri);
            ExifInterface exif = null;
            try {
                exif = new ExifInterface(imagePath);
            }catch (IOException e){
                e.printStackTrace();
            }
            int exifOrientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            int exifDegree = exifOrientationToDegress(exifOrientation);

            bitmap = BitmapFactory.decodeFile(imagePath);

            uploadToServer(imagePath);

            iv.setImageBitmap(rotate(bitmap, exifDegree));
            Bitmap bit = ((BitmapDrawable)iv.getDrawable()).getBitmap();
            OriginPixels = new int[bit.getWidth() * bit.getHeight()];
            bit.getPixels(OriginPixels, 0, bit.getWidth(), 0, 0, bit.getWidth(), bit.getHeight());
        }
    }

    private void goToAlbum() {
        Intent intent = new Intent(Intent.ACTION_PICK);
        intent.setData(MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
        intent.setType("image/*");
        startActivityForResult(intent, PICK_FROM_ALBUM);
    }

    private String getRealPathFromURI(Uri contentUri){
        int column_index = 0;
        String[] proj = {MediaStore.Images.Media.DATA};
        Cursor cursor = getContentResolver().query(contentUri, proj, null, null, null);
        if(cursor.moveToFirst()){
            column_index = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DATA);
        }
        return cursor.getString(column_index);
    }

    private int exifOrientationToDegress(int exifOrientation) {
        if (exifOrientation == ExifInterface.ORIENTATION_ROTATE_90) {
            return 90;
        } else if (exifOrientation == ExifInterface.ORIENTATION_ROTATE_180) {
            return 180;
        } else if (exifOrientation == ExifInterface.ORIENTATION_ROTATE_270) {
            return 270;
        }
        return 0;
    }

    private Bitmap rotate(Bitmap src, float degree){
        if(degree != 0 && src != null){
            Matrix m = new Matrix();
            m.setRotate(degree, (float)src.getWidth() / 2, (float)src.getHeight() / 2);

            try{
                Bitmap converted = Bitmap.createBitmap(src, 0,0,src.getWidth(), src.getHeight(), m, true);
                if(src != converted){
                    src.recycle();
                    src = converted;
                }
            }catch (OutOfMemoryError ex){
                ex.printStackTrace();
            }
        }
        return src;
    }

    public static void uploadToServer(String filePath) {
        File file = new File(filePath);
        Log.d(TAG, "Filename " + file.getName());
        RequestBody mFile = RequestBody.create(MediaType.parse("image/*"), file);
        MultipartBody.Part fileToUpload = MultipartBody.Part.createFormData("file", file.getName(), mFile);
        RequestBody filename = RequestBody.create(MediaType.parse("text/plain"), file.getName());
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
        Call<ResponseBody> call = uploadImage.uploadImage(filename, fileToUpload);

        progressDialog.setProgressStyle(ProgressDialog.STYLE_SPINNER);
        progressDialog.setIndeterminate(true);
        progressDialog.setMessage("Loading...");
        progressDialog.show();

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
                if (response.isSuccessful()) {
                    Log.d(TAG, "server contacted and has file");
                    try {
                        //JsonObject jsonObject = new JsonObject().get(response.body().toString()).getAsJsonObject();
                        assert response.body() != null;
                        String info = response.body().string();
                        info = info.replaceAll("\\[", "").replaceAll("]", "");;
                        ArrayList<Float> temp = new ArrayList<Float>();
                        while(info.length() != 0){
                            if(info.contains(",")){
                                temp.add(Float.parseFloat(info.substring(0, info.indexOf(","))));
                                info = info.substring(info.indexOf(",") + 1);
                            }
                            else{
                                temp.add(Float.parseFloat(info));
                                info = "";
                            }
                            if(temp.size() == 4){
                                LocationArr.add(new Location(temp.get(3), temp.get(2), temp.get(1),temp.get(0)));
                                CheckArr.add(false);
                                temp.clear();
                            }
                        }
                    }catch (NullPointerException E){
                        E.printStackTrace();
                    }catch (IOException e){
                        e.printStackTrace();
                    }
                    for(int i = 0 ; i < LocationArr.size(); i++){
                        Log.d(TAG, Float.toString(LocationArr.get(i).getfloatXdown()) + " " +
                                Float.toString(LocationArr.get(i).getfloatXup()) + " " +
                                Float.toString(LocationArr.get(i).getfloatYdown()) + " " +
                                Float.toString(LocationArr.get(i).getfloatYup()));
                    }
                    progressDialog.dismiss();
                    Log.d(TAG, "Complete");
                } else {
                    Log.d(TAG, "server contact failed");
                    progressDialog.dismiss();
                }
            }
            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
                Log.d(TAG, "fail = " + t.getMessage());
                t.printStackTrace();
                progressDialog.dismiss();
            }
        });
    }
}
