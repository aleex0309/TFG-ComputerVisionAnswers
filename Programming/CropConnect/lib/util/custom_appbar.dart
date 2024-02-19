import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../my_colors.dart';

class CustomAppBar extends StatelessWidget implements PreferredSizeWidget {
  @override
  Widget build(BuildContext context) {
    return PreferredSize(
      preferredSize: Size.fromHeight(60.0),
      child: AppBar(
        centerTitle: false,
        backgroundColor: AppColors.bone,
        elevation: 5.0,
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: IconButton(
                icon: const Icon(
                  Icons.person,
                  size: 30,
                  color: Colors.black, // Cambiado a negro
                ),
                onPressed: () {
                  print("Redirect to userpage"); // TODO: UserPage
                },
              ),
            ),
            const Text(
              'CropConnect',
              style: TextStyle(
                fontFamily: "SanFrancisco",
                color: Colors.black,
                fontWeight: FontWeight.bold,
                fontSize: 20,
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: IconButton(
                icon: const Icon(
                  Icons.exit_to_app,
                  size: 30,
                  color: Colors.black,
                ),
                onPressed: () {
                  FirebaseAuth.instance.signOut();
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Size get preferredSize => Size.fromHeight(60.0);
}