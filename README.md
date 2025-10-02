# Trakt Stats Generator

This project creates a neat SVG image showing the last movie or TV show you watched on Trakt. It's designed to be easily embedded in your GitHub profile README to share what you're currently watching with everyone.

## How It Works

This is a small web application that connects to the Trakt.tv API using your account. It fetches your most recent watch history and then generates a dynamic SVG image card that displays the show or movie's logo, title, and other details.

The whole thing is set up to run smoothly on Vercel, giving you a public link you can use anywhere.

## Setup Instructions

Getting this up and running involves a few steps, but it's pretty straightforward.

### 1. Create a Trakt API App

First, you need to register an application with Trakt to get your API keys.

* Head over to the [**Trakt API Applications page**](https://trakt.tv/oauth/applications) and click "New Application".

* Give your application a name (like "GitHub Stats").

* In the **"Redirect URI"** field, you need to put the URL where your app will be hosted, followed by `/oauth/callback`. If you're using Vercel, it will look something like this: `https://your-app-name.vercel.app/oauth/callback`.

  * *You can come back and edit this later if you don't know the exact URL yet.*

* Save the application. You'll get a **Client ID** and a **Client Secret**. Keep these handy.

### 2. Deploy to Vercel

The easiest way to get this project online is by deploying it to Vercel.

* Deploy this repository to your Vercel account.

* During the import process, Vercel will ask you to configure Environment Variables. Add the following:

  * `TRAKT_USERNAME`: Your Trakt.tv username.

  * `TRAKT_CLIENT_ID`: The Client ID you got in the previous step.

  * `TRAKT_CLIENT_SECRET`: The Client Secret from your Trakt app.

  * `TRAKT_REDIRECT_URI`: The full callback URL you set up earlier (e.g., `https://your-app-name.vercel.app/oauth/callback`).

### 3. Authorize Your Trakt Account

Once the app is deployed, you need to connect it to your Trakt account.

* Open your deployed application's URL in your browser and go to the `/login` path. (e.g., `https://your-app-name.vercel.app/login`).

* This will redirect you to the Trakt website, where it will ask for your permission to access your profile data. Click **"Yes"** to authorize it.

### 4. Add the Final Environment Variables

After authorization, you will be redirected back to a page on your app that displays your authentication tokens.

* The page will show you a `TRAKT_ACCESS_TOKEN`, `TRAKT_REFRESH_TOKEN`, and `TRAKT_TOKEN_EXPIRES_AT`.

* **This is the final key step:** Go back to your project's dashboard on Vercel. Navigate to **Settings -> Environment Variables** and add these three new keys with their corresponding values.

* After adding the new variables, you'll need to trigger a new deployment on Vercel for the changes to take effect. You can usually do this from the "Deployments" tab.

## Usage

You're all set! Your public stats URL is now active. To add it to your GitHub profile, just copy and paste the following markdown into your README file.

Make sure to replace the URL with your own Vercel app URL.
And that's it! Your latest watched item from Trakt will now show up on your profile.

## License

This project is available under the GNU General Public License v3.0.
