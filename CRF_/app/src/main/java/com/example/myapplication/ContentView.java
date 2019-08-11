package com.example.myapplication;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;

import android.app.Activity;
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
import android.widget.ImageView;
import android.widget.Toast;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.DataOutputStream;
import java.io.File;
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

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class ContentView extends AppCompatActivity {

    List<Location> LocationArr = new ArrayList<Location>();
    List<Boolean> CheckArr = new ArrayList<Boolean>();
    private static final String TAG = MainActivity.class.getSimpleName();
    private  File tempFile;
    private  String currentPhotoPath;
    private static final int PICK_FROM_CAMERA = 1;
    private static final int PICK_FROM_ALBUM = 2;
    private  Bitmap bitmap;
    private ImageView iv;
    private final int GAP = 100;
    private final int WEIGHT = 10;
    private int[] OriginPixels;
    private byte[] data;
    private DataOutputStream dos;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_content_view);

         iv = (ImageView)findViewById(R.id.contentview);

        Intent intent = getIntent();
        int num = intent.getExtras().getInt("num");

        switch(num){
            case PICK_FROM_CAMERA:
                LocationArr.add(new Location(522,334, 354,64));
                CheckArr.add(false);
                takePhoto();
                break;
            case PICK_FROM_ALBUM:
                LocationArr.add(new Location(522,334, 354,64));
                CheckArr.add(false);
                goToAlbum();
                break;
            default:
        }

        findViewById(R.id.contentview).setOnTouchListener(new View.OnTouchListener() {
            float floatx, floaty;
                @Override
                public boolean onTouch(View view, MotionEvent motionEvent) {
                    if(motionEvent.getAction() == MotionEvent.ACTION_UP){
                        floatx = motionEvent.getX();
                        floaty = motionEvent.getY();
                        Toast.makeText(getApplicationContext(), floatx + " " + floaty, Toast.LENGTH_SHORT).show();

                        for(int i = 0 ; i < LocationArr.size(); i++){
                            if((LocationArr.get(i).getfloatXup() + GAP >= floatx || LocationArr.get(i).getfloatXdown() - GAP <= floatx) &&
                                (LocationArr.get(i).getfloatYup() + GAP >= floaty || LocationArr.get(i).getfloatYdown() - GAP <= floaty)){
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

        findViewById(R.id.btn_apply).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                Intent intent = new Intent(getApplicationContext(), ResultView.class);
                startActivity(intent);
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

        // 이미지가 저장될 폴더 이름 ( blackJin )
        File Dir = new File(Environment.getExternalStorageDirectory() + "/DCIM/Camera/");
        //File storageDir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), "/");
        //File storageDir = new File(Environment.getExternalStorageDirectory()+ "/blackJin/");
        //File storageDir = new File(Environment.getExternalStoragePublicDirectory());
        if (!Dir.exists()) Dir.mkdirs();

        // 빈 파일 생성
        File storageDir = new File(Environment.getExternalStorageDirectory().getAbsoluteFile() + "/DCIM/Camera/" + imageFileName);
        currentPhotoPath = storageDir.getAbsolutePath();
        //File image = File.createTempFile(imageFileName, ".jpg", storageDir);

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

        if(requestCode == PICK_FROM_CAMERA){ // 카메라
            bitmap = BitmapFactory.decodeFile(currentPhotoPath);
            imageTobtye(bitmap);

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

            iv.setImageBitmap(rotate(bitmap, exifDegree));
            Bitmap bit = ((BitmapDrawable)iv.getDrawable()).getBitmap();
            OriginPixels = new int[bit.getWidth() * bit.getHeight()];
            bit.getPixels(OriginPixels, 0, bit.getWidth(), 0, 0, bit.getWidth(), bit.getHeight());
        }
        else if (requestCode == PICK_FROM_ALBUM) { // 앨범
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
            imageTobtye(bitmap);
            //uploadToServer(imagePath);

            downloadToServer();

            iv.setImageBitmap(rotate(bitmap, exifDegree));
            Bitmap bit = ((BitmapDrawable)iv.getDrawable()).getBitmap();
            OriginPixels = new int[bit.getWidth() * bit.getHeight()];
            bit.getPixels(OriginPixels, 0, bit.getWidth(), 0, 0, bit.getWidth(), bit.getHeight());
        }
    }

    private void imageTobtye(Bitmap bit){
        final int lnth = bit.getByteCount();
        ByteBuffer dst= ByteBuffer.allocate(lnth);
        bitmap.copyPixelsToBuffer(dst);
        data = dst.array();
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

    private void uploadToServer(String filePath) {
        File file = new File(filePath);
        Log.d(TAG, "Filename " + file.getName());
        RequestBody mFile = RequestBody.create(MediaType.parse("image/*"), file);
        MultipartBody.Part fileToUpload = MultipartBody.Part.createFormData("file", file.getName(), mFile);
        RequestBody filename = RequestBody.create(MediaType.parse("text/plain"), file.getName());
        /*Gson gson = new GsonBuilder()
                .setLenient()
                .create();*/
        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(NetworkClient.BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build();
        UploadAPIs uploadImage = retrofit.create(UploadAPIs.class);
        Call<ResponseBody> call = uploadImage.uploadImage(filename, fileToUpload);

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
                if (response.isSuccessful()) {
                    Log.d(TAG, "server contacted and has file");
                } else {
                    Log.d(TAG, "server contact failed");
                }
            }
            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
                Log.d(TAG, "fail = " + t.getMessage());
                t.printStackTrace();
            }
        });
    }

    private void downloadToServer(){
        Retrofit.Builder builder = new Retrofit.Builder()
                .baseUrl(NetworkClient.BASE_URL);

        Retrofit retrofit = builder.build();

        UploadAPIs fileDownloadClient = retrofit.create(UploadAPIs.class);

        Call<ResponseBody> call = fileDownloadClient.downloadFile();

        call.enqueue(new Callback<ResponseBody>() {
            @Override
            public void onResponse(Call<ResponseBody> call, Response<ResponseBody> response) {
                if(response.isSuccessful()){
                    Toast.makeText(getApplicationContext(), "success get image", Toast.LENGTH_LONG).show();
                    boolean success = writeResponseBodyToDisk(response.body());
                    if(success){
                        Toast.makeText(getApplicationContext(), "complete get image", Toast.LENGTH_LONG).show();
                    }
                }
                else {
                    Toast.makeText(getApplicationContext(), "fail get image", Toast.LENGTH_LONG).show();
                }
            }

            @Override
            public void onFailure(Call<ResponseBody> call, Throwable t) {
                Toast.makeText(getApplicationContext(), "fail connect", Toast.LENGTH_LONG).show();
            }
        });
    }

    private boolean writeResponseBodyToDisk(ResponseBody body) {
        try {
            // todo change the file location/name according to your needs
            File futureStudioIconFile = new File(getExternalFilesDir(null) + File.separator + "Future Studio Icon.png");

            InputStream inputStream = null;
            OutputStream outputStream = null;

            try {
                byte[] fileReader = new byte[4096];

                long fileSize = body.contentLength();
                long fileSizeDownloaded = 0;

                inputStream = body.byteStream();
                outputStream = new FileOutputStream(futureStudioIconFile);

                while (true) {
                    int read = inputStream.read(fileReader);

                    if (read == -1) {
                        break;
                    }

                    outputStream.write(fileReader, 0, read);

                    fileSizeDownloaded += read;

                    Log.d(TAG, "file download: " + fileSizeDownloaded + " of " + fileSize);
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
            }
        } catch (IOException e) {
            return false;
        }
    }


}
