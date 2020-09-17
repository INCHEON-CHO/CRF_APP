package com.example.myapplication;

import android.os.Bundle;
import android.view.View;

import androidx.appcompat.app.AppCompatActivity;

public class EditActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        //setContentView(R.layout.activity_edit);
        //init();
    }

    /*private void init() {
        findViewById(R.id.edit_ly_header).setOnClickListener(view -> {
            finish();
        });
        findViewById(R.id.edit_ly_confirm).setOnClickListener(view -> {

            findViewById(R.id.edit_ly_btns).setVisibility(View.GONE);
            findViewById(R.id.edit_ly_complete).setVisibility(View.VISIBLE);
        });
    }*/
}
