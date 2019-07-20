package com.example.myapplication;

import androidx.appcompat.app.AppCompatActivity;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.os.Bundle;
import android.widget.ImageView;

public class ContentView extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_content_view);

        Intent intent = getIntent();
        Bitmap bitmap = (Bitmap)intent.getExtras().get("bitmap");
        int exifDegree = intent.getExtras().getInt("Degree");

        ((ImageView)findViewById(R.id.imageView)).setImageBitmap(rotate(bitmap, exifDegree));
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
