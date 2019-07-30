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

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class ContentView extends AppCompatActivity {

    List<Location> LocationArr = new ArrayList<Location>();
    private static final String TAG = "blackjin";
    private  File tempFile;
    private  String currentPhotoPath;
    private static final int PICK_FROM_CAMERA = 1;
    private static final int PICK_FROM_ALBUM = 2;
    private  Bitmap bitmap;
    private ImageView iv;
    private final int GAP = 50;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_content_view);

         iv = (ImageView)findViewById(R.id.resultview);

        Intent intent = getIntent();
        int num = intent.getExtras().getInt("num");

        switch(num){
            case PICK_FROM_CAMERA:
                LocationArr.add(new Location(52,3, 354,64));
                takePhoto();
                break;
            case PICK_FROM_ALBUM:
                LocationArr.add(new Location(52,3, 354,64));
                goToAlbum();
                break;
            default:
        }

        findViewById(R.id.resultview).setOnTouchListener(new View.OnTouchListener() {
            float floatx, floaty;
                @Override
                public boolean onTouch(View view, MotionEvent motionEvent) {
                    if(motionEvent.getAction() == MotionEvent.ACTION_UP){
                        floatx = motionEvent.getX();
                        floaty = motionEvent.getY();
                        Toast.makeText(getApplicationContext(), floatx + " " + floaty, Toast.LENGTH_SHORT).show();

                        for(int i = 0 ; i < LocationArr.size(); i++){
                            if((Math.abs(floatx - LocationArr.get(i).getfloatXup()) < GAP || Math.abs(floatx - LocationArr.get(i).getfloatXdown()) < GAP) &&
                                    (Math.abs(floaty - LocationArr.get(i).getfloatYup()) < GAP || Math.abs(floaty - LocationArr.get(i).getfloatYdown()) < GAP)){
                        Bitmap bit = ((BitmapDrawable)iv.getDrawable()).getBitmap();
                        Bitmap ModifiedBitmap = changeColor(bit, LocationArr.get(i).getfloatXdown(), LocationArr.get(i).getfloatXup(), LocationArr.get(i).getfloatYdown(), LocationArr.get(i).getfloatYup());
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

    private Bitmap changeColor(Bitmap src, float upX, float downX, float upY, float downY) {
        int width = src.getWidth();
        int height = src.getHeight();
        int[] pixels = new int[width * height];
        // get pixel array from source
        src.getPixels(pixels, 0, width, 0, 0, width, height);

        Bitmap bmOut = Bitmap.createBitmap(width, height, src.getConfig());

        for (int y = (int)downY; y < (int)upY; ++y) {
            for (int x = (int)downX; x < (int)upX; ++x) {
                // get current index in 2D-matrix
                int index = y * width + x;

                //pixel = pixels[index];
                //change A-RGB individually
                //A = Color.alpha(colorThatWillReplace);
                //R = Color.red(colorThatWillReplace);
                //G = Color.green(colorThatWillReplace);
                //B = Color.blue(colorThatWillReplace);
                pixels[index] = Color.argb(255, 255, 0, 0);
                /*or change the whole color
                pixels[index] = colorThatWillReplace;
                pixels[index] = 1;
            }
        }*/
            }
        }
        bmOut.setPixels(pixels, 0, width, 0, 0, width, height);
        return bmOut;

        /*int A, R, G, B;
        int pixel;

        // iteration through pixels
        for (int y = (int)downY; y < (int)upY; ++y) {
            for (int x = (int)downX; x < (int)upX; ++x) {
                // get current index in 2D-matrix
                int index = y * width + x;
                //pixel = pixels[index];
                //change A-RGB individually
                //A = Color.alpha(colorThatWillReplace);
                //R = Color.red(colorThatWillReplace);
                //G = Color.green(colorThatWillReplace);
                //B = Color.blue(colorThatWillReplace);
                pixels[index] = Color.argb(255,255,0,0);
                /*or change the whole color
                pixels[index] = colorThatWillReplace;
                pixels[index] = 1;
            }
        }
        bmOut.setPixels(pixels, 0, width, 0, 0, width, height);
        return bmOut;*/
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

            ((ImageView)findViewById(R.id.resultview)).setImageBitmap(rotate(bitmap, exifDegree));
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

            ((ImageView)findViewById(R.id.resultview)).setImageBitmap(rotate(bitmap, exifDegree));
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
}
