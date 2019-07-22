package com.example.myapplication;

public class Location {
    private float floatXup;
    private float floatYup;
    private float floatXdown;
    private float floatYdown;

    public Location(float floatXup, float floatYup, float floatXdown, float floatYdown) {
        this.floatXup = floatXup;
        this.floatYup = floatYup;
        this.floatXdown = floatXdown;
        this.floatYdown = floatYdown;
    }

    @Override
    public String toString() {
        return "Location{" +
                "floatXup=" + floatXup +
                ", floatYup=" + floatYup +
                ", floatXdown=" + floatXdown +
                ", floatYdown=" + floatYdown +
                '}';
    }

    public void setfloatXup(float floatXup) {
        this.floatXup = floatXup;
    }

    public void setfloatYup(float floatYup) {
        this.floatYup = floatYup;
    }

    public void setfloatXdown(float floatXdown) {
        this.floatXdown = floatXdown;
    }

    public void setfloatYdown(float floatYdown) {
        this.floatYdown = floatYdown;
    }

    public float getfloatXup() {
        return floatXup;
    }

    public float getfloatYup() {
        return floatYup;
    }

    public float getfloatXdown() {
        return floatXdown;
    }

    public float getfloatYdown() {
        return floatYdown;
    }



}
