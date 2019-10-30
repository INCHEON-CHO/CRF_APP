## Image Creating Service

사진 속에 찍힌 불필요한 객체를 지워주는 mobile 서비스 제공을 목표로 하는 프로젝트

원하는 사진을 제공함으로써 사진에 대한 만족감을 키울 수 있다.

Facebook, SNS에 사진, 스토리 등으로 공유하면서 어플의 사용성을 키울 수 있다.

* Deep Learning
  * instance segmentation
    * 사진 속 객체의 위치를 파악할 수 있다.
    * 각각의 객체에 대해 index 처리가 가능하다.
  * image inpainting
    * 객체를 지운 부분의 사진을 자연스럽게 채울 수 있도록 도와준다.
    * Wasserstein GAN이라는 기술을 기반으로 만들어지는 기술이다.
* APP 
  * UI
    * 앱의 기본적인 기능을 Android Studio를 통해 구현
    * Android 환경에서의 작동이 가능
  * Disign - 디자인 부분은 외주를 통하여 더 깔끔한 디자인을 제공할 예정

