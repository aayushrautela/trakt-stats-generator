# Trakt Stats Generator

This project creates a neat SVG image showing the last movie or TV show you watched on Trakt. It's designed to be easily embedded in your GitHub profile README to share what you're currently watching with everyone.

 ![My Trakt Stats](https://trakt-stats-generator.vercel.app/api/trakt/public)

## How It Works

This is a small web application that connects to the Trakt.tv API using your account. It fetches your most recent watch history and then generates a dynamic SVG image card that displays the show or movie's logo, title, and other details.

**🔄 Automatic Token Management**: The app now uses Redis storage for persistent token management, automatically refreshing your Trakt credentials before they expire. No more manual token updates needed!

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

### 3. Set Up Redis Storage

The app uses Redis for automatic token management. You need to add Redis storage to your Vercel project:

* Go to your Vercel project dashboard
* Navigate to the **Storage** tab
* Click **"Create"** on the **Upstash** option
* Follow the setup wizard to create your Redis database
* Vercel will automatically add the required environment variables (`REDIS_URL` and `KV_REST_API_TOKEN`)

### 4. Authorize Your Trakt Account

Once the app is deployed and Redis is set up, you need to connect it to your Trakt account.

* Open your deployed application's URL in your browser and go to the `/login` path. (e.g., `https://your-app-name.vercel.app/login`).

* This will redirect you to the Trakt website, where it will ask for your permission to access your profile data. Click **"Yes"** to authorize it.

* After authorization, you'll be redirected back to a success page. Your tokens will be automatically saved to Redis storage.

**🎉 That's it!** No manual token management needed - the app will automatically refresh your credentials before they expire.

## Usage

You're all set! Your public stats URL is now active. To add it to your GitHub profile, just copy and paste the following markdown into your README file.

```markdown
![My Trakt Stats](https://your-app-name.vercel.app/api/trakt/public)
```

* Make sure to replace the URL with your own Vercel app URL.

And that's it! Your latest watched item from Trakt will now show up on your profile.

## Features

* **🔄 Automatic Token Refresh**: No more manual token updates - the app handles everything automatically
* **💾 Persistent Storage**: Tokens are stored in Redis, surviving deployments and cold starts
* **⚡ Real-time Updates**: Your stats update automatically as you watch new content
* **🎨 Beautiful SVG Cards**: Clean, responsive design that looks great on any profile
* **🔒 Secure**: All sensitive data is stored securely in Vercel's infrastructure

## Troubleshooting

If you encounter any issues:

1. **Check your Redis connection**: Ensure the Upstash Redis database is properly set up
2. **Verify environment variables**: Make sure all required variables are set in Vercel
3. **Test the refresh endpoint**: Visit `/api/refresh-token` to manually test token refresh
4. **Check the logs**: Monitor your Vercel function logs for any error messages

## License

This project is available under the GNU General Public License v3.0.
